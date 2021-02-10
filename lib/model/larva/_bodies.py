import abc
from random import sample, seed

import Box2D
from Box2D import b2Vec2

# TODO Find a way to use this. Now if changed everything is scal except locomotion. It seems that
#  ApplyForceToCenter function does not scale
# _world_scale = np.int(100)
from lib.aux.functions import *


class Body:

    def __init__(self, model, position=None, orientation=None, facing_axis=None, joint_type=None,
                 seg_lengths=None, Nsegs=1, seg_vertices=None, length=None):

        if self.model.physics_engine:
            self.physics_pars = {'density': self.density,
                                   'friction': 0.01,
                                   'restitution': 0.0,
                                   'lin_damping': self.lin_damping,
                                   'ang_damping': self.ang_damping,
                                   'inertia': 1.0}
        else:
            self.physics_pars = None

        self.model = model
        self.seg_lengths = seg_lengths
        self.Nsegs = Nsegs
        self.seg_vertices = seg_vertices

        self.local_rear_end_of_head = (np.min(self.seg_vertices[0][0], axis=0)[0], 0)
        self.local_front_end_of_head = (np.max(self.seg_vertices[0][0], axis=0)[0], 0)

        # segment_length_x = seg_lengths * np.cos(orientation)
        seg_lengths_x = [np.cos(orientation) * l for l in self.seg_lengths]
        seg_lengths_y = np.sin(orientation) * length / self.Nsegs
        seg_positions = [[position[0] + (-i + (Nsegs - 1) / 2) * seg_lengths_x[i],
                              position[1] + (-i + (Nsegs - 1) / 2) * seg_lengths_y] for i in
                             range(Nsegs)]
        self.segs = []
        if self.Nsegs>5 :
            self.seg_colors = [np.array((0, 255, 0))] + [np.copy(self.default_color) for i in range(self.Nsegs - 2)] + [np.array((255, 0, 0))]
        else :
            self.seg_colors = [np.copy(self.default_color) for i in range(self.Nsegs)]

        if self.model.physics_engine:
            self._fixtures = []
            for i in range(Nsegs):
                seg = Polygon(space=self.model.space, pos=seg_positions[i], orientation=orientation,
                              physics_pars=self.physics_pars, facing_axis=facing_axis,
                              seg_vertices=self.seg_vertices[i], color=self.seg_colors[i])
                self._fixtures.extend(seg._fixtures)
                self.segs.append(seg)

            # put all agents into same group (negative so that no collisions are detected)
            for fixture in self._fixtures:
                fixture.filterData.groupIndex = -1

            if joint_type is None:
                joint_type = {'distance': 2, 'revolute': 1}
            if Nsegs > 1:
                self.create_joints(Nsegs, joint_type)
        else:
            for i in range(Nsegs):
                seg = PolygonShape(pos=seg_positions[i], orientation=orientation,
                                   seg_vertices=self.seg_vertices[i], color=self.seg_colors[i])
                self.segs.append(seg)
            self.model.space.place_agent(self, self.get_global_midspine_of_body())
            # space.place_agent(self, position)
        self.Nangles = self.Nsegs - 1
        self.spineangles = np.zeros(self.Nangles)
        self.set_contour()



    def create_joints(self, num_segments, joint_type):
        space=self.model.space

        # TODO Find compatible parameters.
        # Until now for the 12-seg body : density 30000 and maxForce 100000000  and torque_coef 3.5 seem to work for natural bend
        # Trying to implement friction joint
        # friction_joint = False
        if self.friction_pars is not None:
            friction_pars=self.friction_pars
            # print('lala')
            friction_joint_def = {'maxForce': friction_pars['maxForce'],
                                  # Good for one segment maybe : 100000000,
                                  'maxTorque': friction_pars[
                                      'maxTorque']}  # Good for one segment maybe : 10,
            for i in range(num_segments):
                friction_joint = space.CreateFrictionJoint(**friction_joint_def,
                                                           bodyA=self.segs[i]._body,
                                                           bodyB=self.model.friction_body,
                                                           localAnchorA=(0, 0),
                                                           localAnchorB=(0, 0))

        self.joints = []
        # This gets the extreme lateral points:
        lateral_attachment_dist = self.width_to_length_ratio * self.Nsegs / 2
        # For many segments, the front one(s) will be joint by points outside the body.
        # So we adopt a more conservative solution, bringing the attachment point more medially : No visible difference
        # lateral_attachment_dist = self.width_to_length_ratio * self.Npoints / 4

        if joint_type['distance']:
            dist_joint_def = {'collideConnected': False,
                              'frequencyHz': 5,
                              'dampingRatio': 1,
                              'length': np.mean(self.seg_lengths) * 0.01}

            for i in range(num_segments - 1):
                if joint_type['distance'] == 2:
                    left_joint = space.CreateDistanceJoint(**dist_joint_def,
                                                           bodyA=self.segs[i]._body,
                                                           bodyB=self.segs[i + 1]._body,
                                                           localAnchorA=tuple(np.mean(self.seg_lengths) * x for x in
                                                                                   (-0.5, lateral_attachment_dist)),
                                                           localAnchorB=tuple(
                                                                    np.mean(self.seg_lengths) * x for x in
                                                                    (0.5, lateral_attachment_dist))
                                                           )
                    right_joint = space.CreateDistanceJoint(**dist_joint_def,
                                                            bodyA=self.segs[i]._body,
                                                            bodyB=self.segs[i + 1]._body,
                                                            localAnchorA=tuple(
                                                                     np.mean(self.seg_lengths) * x for x in
                                                                     (-0.5,
                                                                      -lateral_attachment_dist)),
                                                            localAnchorB=tuple(
                                                                     np.mean(self.seg_lengths) * x for x in
                                                                     (0.5, -lateral_attachment_dist))
                                                            )
                    self.joints.append([left_joint, right_joint])
                elif joint_type['distance'] == 1:
                    joint = space.CreateDistanceJoint(**dist_joint_def,
                                                      bodyA=self.segs[i]._body,
                                                      bodyB=self.segs[i + 1]._body,
                                                      localAnchorA=tuple(np.mean(self.seg_lengths) * x for x in
                                                                              (-0.5, 0)),
                                                      localAnchorB=tuple(
                                                               np.mean(self.seg_lengths) * x for x in (0.5, 0))
                                                      )
                    self.joints.append(joint)

        if joint_type['revolute']:

            rev_joint_def = {'collideConnected': False,
                             'referenceAngle': 0,
                             'enableLimit': True,
                             'lowerAngle': -(np.pi / 2) / self.Nsegs,
                             'upperAngle': (np.pi / 2) / self.Nsegs,
                             'enableMotor': True,  # )
                             'maxMotorTorque': 0.1,
                             'motorSpeed': 0}

            for i in range(num_segments - 1):
                if joint_type['revolute'] == 2:
                    left_joint = space.CreateRevoluteJoint(**rev_joint_def,
                                                           bodyA=self.segs[i]._body,
                                                           bodyB=self.segs[i + 1]._body,
                                                           localAnchorA=tuple(np.mean(self.seg_lengths) * x for x in
                                                                                   (-0.5, lateral_attachment_dist)),
                                                           localAnchorB=tuple(
                                                                    np.mean(self.seg_lengths) * x for x in
                                                                    (0.5, lateral_attachment_dist))
                                                           )
                    right_joint = space.CreateRevoluteJoint(**rev_joint_def,
                                                            bodyA=self.segs[i]._body,
                                                            bodyB=self.segs[i + 1]._body,
                                                            localAnchorA=tuple(
                                                                     np.mean(self.seg_lengths) * x for x in
                                                                     (-0.5,
                                                                      -lateral_attachment_dist)),
                                                            localAnchorB=tuple(
                                                                     np.mean(self.seg_lengths) * x for x in
                                                                     (0.5, -lateral_attachment_dist))
                                                            )
                    self.joints.append([left_joint, right_joint])
                elif joint_type['revolute'] == 1:
                    joint = space.CreateRevoluteJoint(**rev_joint_def,
                                                      bodyA=self.segs[i]._body,
                                                      bodyB=self.segs[i + 1]._body,
                                                      localAnchorA=tuple(
                                                          np.mean(self.seg_lengths) * x for x in (-0.5, 0)),
                                                      localAnchorB=tuple(
                                                          np.mean(self.seg_lengths) * x for x in (0.5, 0)))
                    self.joints.append(joint)

    # FIXME Fix the deletion of segments/agents
    def __del__(self):
        try:
            for seg in self.segs:
                self.space.DestroyBody(seg._body)
        except:
            try:
                self.space.remove_agent(self)
            except:
                pass

    def draw(self, viewer):
        if not self.model.draw_contour:
            viewer.draw_polygon(self.contour, filled=True, color=self.get_head()._color)
        else:
            self.set_contour()
            for seg in self.segs:
                seg.draw(viewer)
        if self.model.draw_head:
            viewer.draw_circle(radius=self.seg_lengths[0] / 2,
                               position=self.get_global_front_end_of_head(),
                               filled=True, color=(255, 0, 0), width=.1)

    def plot_vertices(self, axes, **kwargs):
        for seg in self.segs:
            seg.plot(axes, **kwargs)

    def get_mass(self):
        mass = 0
        for seg in self.segs:
            mass += seg.get_mass()
        return mass

    def set_color(self, color):
        for seg, col in zip(self.segs, color) :
            seg.set_color(col)

    def get_color(self):
        return [seg.get_color() for seg in self.segs]

    # def get_head_orientation(self):
    #     return self.segs[0].get_orientation()

    def get_segment(self, seg_index):
        return self.segs[seg_index]

    def get_head(self):
        return self.segs[0]

    def get_tail(self):
        return self.segs[-1]

    def get_centroid_position(self):
        seg_x_positions = []
        seg_y_positions = []
        for i, seg in enumerate(self.segs):
            # print(i, seg.get_position())
            x, y = seg.get_position().tolist()

            seg_x_positions.append(x)
            seg_y_positions.append(y)
        centroid = (sum(seg_x_positions) / len(self.segs), sum(seg_y_positions) / len(self.segs))

        return np.asarray(centroid)

    def get_local_front_end_of_seg(self, seg_index):
        front_local_x = np.max(self.seg_vertices[seg_index][0], axis=0)[0]
        return (front_local_x, 0)

    def get_local_rear_end_of_seg(self, seg_index):
        rear_local_x = np.min(self.seg_vertices[seg_index][0], axis=0)[0]
        return (rear_local_x, 0)

    def get_local_rear_end_of_head(self):
        return self.local_rear_end_of_head

    def get_local_front_end_of_head(self):
        return self.local_front_end_of_head

    def get_global_front_end_of_seg(self, seg_index):
        local_pos=self.get_local_front_end_of_seg(seg_index)
        global_pos = self.get_segment(seg_index).get_world_point(local_pos)
        return global_pos

    def get_global_rear_end_of_seg(self, seg_index):
        local_pos=self.get_local_rear_end_of_seg(seg_index)
        global_pos = self.get_segment(seg_index).get_world_point(local_pos)
        return global_pos

    def get_global_rear_end_of_head(self):
        return self.segs[0].get_world_point(self.local_rear_end_of_head)

    def get_global_front_end_of_head(self):
        return self.segs[0].get_world_point(self.local_front_end_of_head)

    def get_global_midspine_of_body(self):
        if self.Nsegs==2 :
            return self.get_global_rear_end_of_head()
        if (self.Nsegs % 2) == 0:
            seg_idx = int(self.Nsegs / 2)
            global_pos = self.get_global_front_end_of_seg(seg_idx)
        else:
            seg_idx = int((self.Nsegs + 1) / 2)
            global_pos = self.segs[seg_idx].get_world_point((0.0, 0.0))
        return global_pos


    def get_global_rear_end_of_body(self):
        local_pos = self.get_local_rear_end_of_seg(-1)
        global_pos = self.segs[-1].get_world_point(local_pos)
        return global_pos

    def get_contour(self):
        return self.contour

    def set_contour(self, num_points=22):
        vertices = [np.array(seg.vertices[0]) for seg in self.segs]
        l_side = flatten_list([v[:int(len(v) / 2)] for v in vertices])
        r_side = flatten_list([np.flip(v[int(len(v) / 2):], axis=0) for v in vertices])
        r_side.reverse()
        total_contour = l_side + r_side
        if len(total_contour) > num_points:
            seed(1)
            contour = [total_contour[i] for i in sorted(sample(range(len(total_contour)), num_points))]
        else:
            contour = total_contour
        # self.contour = contour[ConvexHull(contour).vertices].tolist()
        self.contour = contour


class BodySegment:

    def __init__(self, space: Box2D.b2World, pos, orientation, physics_pars, facing_axis, color, **kwargs):
        # super().__init__(**kwargs)
        if self.__class__ == BodySegment:
            raise NotImplementedError('Abstract class BodySegment cannot be instantiated.')
        self.physics_pars = physics_pars
        # print(color)
        self._color = color
        # self._highlight_color = np.array((238, 80, 62))

        # self.space = space
        self._body: Box2D.b2Body = space.CreateDynamicBody(
            position=Box2D.b2Vec2(*pos),
            angle=orientation,
            linearDamping=physics_pars['lin_damping'],
            angularDamping=physics_pars['ang_damping'])
        self._body.linearVelocity = Box2D.b2Vec2(*[.0, .0])
        self._body.angularVelocity = .0
        self._body.bullet = True

        # overriden by LarvaBody
        self.facing_axis = facing_axis

        # CAUTION
        # This sets the body's origin (where position, orientation is derived from)
        # self._body.localCenter = b2Vec2(0.0, 0.0)
        # this sets the body' center of mass (where velocity is set etc)
        # self._body.massData.center= self._body.localCenter
        # self._body.massData.center= b2Vec2(0.0, 0.0)
        # self._body.localCenter = self._body.massData.center

    # @property
    # def width(self):
    #     raise NotImplementedError

    # @property
    # def height(self):
    #     raise NotImplementedError

    # @property
    def get_position(self):
        # CAUTION CAUTION This took me a whole day.
        # worldCenter gets the point where the torque is applied
        # position gets a point (tried to identify whether it is center of mass or origin, no luck) unknown how
        pos = self._body.worldCenter
        # print(pos)
        return np.asarray(pos)

    def set_position(self, position):
        self._body.position = position

    def get_orientation(self):
        angle = self._body.angle
        return angle

    def get_normalized_orientation(self):
        angle = self.get_orientation()
        # I normalize the angle_to_x_axis in [-pi,pi]
        angle %= 2 * np.pi
        # if angle > np.pi:
        #     angle -= 2 * np.pi
        return angle

    def get_linearvelocity_vec(self):
        return self._body.linearVelocity

    def get_linearvelocity_amp(self):
        return np.linalg.norm(self._body.linearVelocity)

    def get_angularvelocity(self):
        return self._body.angularVelocity

    def set_orientation(self, orientation):
        # orientation %= 2 * np.pi
        self._body.angle = orientation

    def get_pose(self):
        pos = np.asarray(self._body.position)
        return tuple((*pos, self._body.angle))

    def set_pose(self, pose):
        self.set_position(pose[:2])
        self.set_orientation(pose[2])

    def set_lin_vel(self, lin_vel, local=False):
        if local:
            lin_vel = self._body.GetWorldVector(np.asarray(lin_vel))
        self._body.linearVelocity = Box2D.b2Vec2(lin_vel)

    def set_ang_vel(self, ang_vel):
        self._body.angularVelocity = ang_vel

    # Panos

    def set_mass(self, mass):
        self._body.mass = mass

    def get_mass(self):
        return self._body.mass

    def add_mass(self, added_mass):
        self._body.mass += added_mass

    def set_massdata(self, massdata):
        self._body.massData = massdata

    def get_state(self):
        return self.get_pose()
        # return tuple((*self._body.position, self._body.angle_to_x_axis))

    def get_local_point(self, point):
        return np.asarray(self._body.GetLocalPoint(np.asarray(point)))

    def get_local_vector(self, vector):
        return np.asarray(self._body.GetLocalVector(vector))

    def get_local_orientation(self, angle):
        return angle - self._body.angle

    def get_local_pose(self, pose):
        return tuple((*self.get_local_point(pose[:2]), self.get_local_orientation(pose[2])))

    def get_world_point(self, point):
        return self._body.GetWorldPoint(np.asarray(point))

    def get_world_vector(self, vector):
        return np.asarray(self._body.GetWorldVector(vector))

    def get_world_facing_axis(self):
        # print(self._body.GetWorldVector(self.facing_axis))
        return np.asarray(self._body.GetWorldVector(self.facing_axis))

    def collides_with(self, other):
        for contact_edge in self._body.contacts_gen:
            if contact_edge.other == other and contact_edge.contact.touching:
                return True

    # def set_color(self, color):
    #     self._color = color
    #
    # def set_highlight_color(self, color):
    #     self._highlight_color = color

    # @property
    def get_color(self):
        return self._color

    # @color.setter
    def set_color(self, color):
        color = np.asarray(color, dtype=np.int32)
        color = np.maximum(color, np.zeros_like(color, dtype=np.int32))
        color = np.minimum(color, np.full_like(color, 255, dtype=np.int32))
        self._color = color

    @property
    def highlight_color(self):
        return self._highlight_color

    @highlight_color.setter
    def highlight_color(self, color):
        color = np.asarray(color, dtype=np.int32)
        color = np.maximum(color, np.zeros_like(color, dtype=np.int32))
        color = np.minimum(color, np.full_like(color, 255, dtype=np.int32))
        self._highlight_color = color

    @abc.abstractmethod
    def draw(self, viewer):
        raise NotImplementedError('The draw method needs to be implemented by the subclass of BodySegment.')

    @abc.abstractmethod
    def plot(self, axes, **kwargs):
        raise NotImplementedError('The plot method needs to be implemented by the subclass of BodySegment.')


# class Quad(BodySegment):
#     def __init__(self, width, height, **kwargs):
#         super().__init__(**kwargs)
#
#         self._width = width
#         self._height = height
#
#         self._fixture = self._body.CreatePolygonFixture(
#             box=Box2D.b2Vec2(self._width / 2, self._height / 2),
#             density=self.physics_pars['density'],
#             friction=self.physics_pars['friction'],
#             restitution=self.physics_pars['restitution'],
#             # radius=.000001
#         )
#
#     @property
#     def width(self):
#         return self._width
#
#     @property
#     def height(self):
#         return self._height
#
#     @property
#     def vertices(self):
#         return np.asarray([[self._body.GetWorldPoint(v) for v in self._fixture.shape.vertices]])
#
#     def draw(self, viewer):
#         viewer.draw_polygon(self.vertices[0], filled=True, color=self._color)
#
#     def plot(self, axes, **kwargs):
#         from simulation.tools.plotting import plot_rect
#         return plot_rect(axes, self, **kwargs)
#
#     def get_width(self):
#         return self._width
#
#     def get_height(self):
#         return self._height


# class Circle(BodySegment):
#     def __init__(self, radius, **kwargs):
#         super().__init__(**kwargs)
#
#         self._radius = radius
#
#         self._fixture = self._body.CreateCircleFixture(
#             radius=self._radius,
#             density=self.physics_pars['density'],
#             friction=self.physics_pars['friction'],
#             restitution=self.physics_pars['restitution']
#         )
#
#     @property
#     def width(self):
#         return 2 * self._radius
#
#     @property
#     def height(self):
#         return 2 * self._radius
#
#     def draw(self, viewer):
#         viewer.draw_aacircle(position=self.get_position(), radius=self._radius, color=self._color)
#
#     @property
#     def vertices(self):
#         return np.array([[self.get_position()]])
#
#     def get_radius(self):
#         return self._radius
#
#     def plot(self, axes, **kwargs):
#         from simulation.tools.plotting import plot_circle
#         return plot_circle(axes, self, **kwargs)


class Polygon(BodySegment):
    def __init__(self, seg_vertices=None, **kwargs):
        super().__init__(**kwargs)

        # TODO: right now this assumes that all subpolygons have the same number of edges
        # TODO: rewrite such that arbitrary subpolygons can be used here
        vertices = seg_vertices

        centroid = np.zeros(2)
        area = .0
        for vs in vertices:
            # compute centroid of circle_to_polygon
            r0 = np.roll(vs[:, 0], 1)
            r1 = np.roll(vs[:, 1], 1)
            a = 0.5 * np.abs(np.dot(vs[:, 0], r1) - np.dot(vs[:, 1], r0))
            area += a
            # FIXME This changed in refactoring. It is wrong probably.
            # Find a way to use compute_centroid(points) function
            centroid += np.mean(vs, axis=0) * a

        centroid /= area

        self.__local_vertices = vertices - centroid
        self.__local_vertices.setflags(write=False)
        for v in self.__local_vertices:
            self._body.CreatePolygonFixture(
                shape=Box2D.b2PolygonShape(vertices=v.tolist()),
                density=self.physics_pars['density'],
                friction=self.physics_pars['friction'],
                restitution=self.physics_pars['restitution'],
                # radius=.00000001
            )

        self._fixtures = self._body.fixtures
        # print(self._body.inertia)
        self._body.inertia = self.physics_pars['inertia']

    # @property
    # def width(self):
    #     return self._width
    #
    # @property
    # def height(self):
    #     return self._height

    @property
    def vertices(self):
        return np.array([[self.get_world_point(v) for v in vertices] for vertices in self.__local_vertices])

    @property
    def local_vertices(self):
        return self.__local_vertices

    @property
    def plot_vertices(self):
        raise NotImplementedError

    # @staticmethod
    # def _shape_vertices() -> np.ndarray:
    #     raise NotImplementedError

    def draw(self, viewer):
        for i, vertices in enumerate(self.vertices):

            viewer.draw_polygon(vertices, filled=True, color=self._color)

    # def plot(self, axes, **kwargs):
    #     from simulation.tools.plotting import plot_polygon
    #     return plot_polygon(axes, self, **kwargs)


class PolygonShape:
    def __init__(self, pos, orientation, seg_vertices, color):
        self.pos = pos
        self.orientation = orientation
        self.seg_vertices = seg_vertices
        self.vertices = None
        self.update_vertices(self.pos, self.orientation)

        self.lin_vel = 0.0
        self.ang_vel = 0.0
        self._color = color
        # print(self._color)
        # centroid = np.zeros(2)
        # area = .0
        # for vs in self.vertices:
        #     print(vs)
        #     # compute centroid of circle_to_polygon
        #     r0 = np.roll(vs[:, 0], 1)
        #     r1 = np.roll(vs[:, 1], 1)
        #     a = 0.5 * np.abs(np.dot(vs[:, 0], r1) - np.dot(vs[:, 1], r0))
        #     area += a
        #     centroid += vs.mean(axis=0) * a
        # centroid /= area

    def update_vertices(self, pos, orient):
        self.vertices = [pos + np.array(rotate_around_center_multi(self.seg_vertices[0], -orient))]


    def draw(self, viewer):
        for vertices in self.vertices:
            viewer.draw_polygon(vertices, filled=True, color=self._color)

    def get_position(self):
        return np.array(self.pos)

    def set_position(self, pos):
        self.pos = pos

    def set_pose(self, pos, orientation, lin_vel, ang_vel):
        self.pos = pos
        self.orientation = orientation
        self.lin_vel = lin_vel
        self.ang_vel = ang_vel

    def get_pose(self):
        return np.array(self.pos), self.orientation

    def get_world_point(self, local_point):
        return self.get_position()+np.array(rotate_around_center(point=local_point, radians=-self.get_orientation()))

    def get_orientation(self):
        return self.orientation

    def get_normalized_orientation(self):
        angle = self.get_orientation()
        # I normalize the angle_to_x_axis in [-pi,pi]
        angle %= 2 * np.pi
        # if angle > np.pi:
        #     angle -= 2 * np.pi
        return angle

    def set_orientation(self, orientation):
        self.orientation = orientation

    def get_linearvelocity_amp(self):
        return self.lin_vel

    def get_angularvelocity(self):
        return self.ang_vel

    def set_linear_velocity(self, lin_vel):
        self.lin_vel = lin_vel

    def set_ang_vel(self, ang_vel):
        self.ang_vel = ang_vel

    def set_color(self, color):
        color = np.asarray(color, dtype=np.int32)
        color = np.maximum(color, np.zeros_like(color, dtype=np.int32))
        color = np.minimum(color, np.full_like(color, 255, dtype=np.int32))
        self._color = color

    def get_color(self):
        return self._color





class LarvaBody(Body):
    def __init__(self, model, pos=None, orientation=None,
                 initial_length=None, length_std=0, Nsegs=1, interval=0, joint_type=None,
                 seg_ratio=None):
        # FIXME get rid of this
        if not 'density' in locals():
            self.density = 300.0

        self.width_to_length_ratio = 0.2
        if seg_ratio is None:
            seg_ratio = [1 / Nsegs] * Nsegs
        self.seg_ratio = seg_ratio
        self.interval = interval
        self.shape_scale = 1

        self.base_seg_vertices = self.generate_segment_shapes(Nsegs, self.width_to_length_ratio,
                                                              density=self.density, interval=self.interval,
                                                              segment_ratio=self.seg_ratio)
        self.Nsegs = Nsegs

        if not hasattr(self, 'real_length'):
            self.real_length = None
        if self.real_length is None :
            self.real_length = float(np.random.normal(loc=initial_length, scale=length_std, size=1))

        self.sim_length = self.real_length * model.scaling_factor
        self.seg_lengths = [self.sim_length * r for r in self.seg_ratio]
        self.seg_vertices = [v * self.sim_length / self.Nsegs for v in self.base_seg_vertices]

        if not hasattr(self, 'real_mass'):
            self.real_mass = None
        if self.real_mass is None :
            self.compute_mass_from_length()


        super().__init__(model=model, position=pos, orientation=orientation,
                         seg_vertices=self.seg_vertices, Nsegs=Nsegs,
                         seg_lengths=self.seg_lengths, length=self.sim_length,
                         facing_axis=b2Vec2(1.0, 0.0), joint_type=joint_type)

    def get_real_length(self):
        return self.real_length

    def get_sim_length(self):
        return self.sim_length

    def get_real_mass(self):
        return self.real_mass

    # def get_sim_mass(self):
    #     return self.sim_mass

    '''We make the following assumptions :
        1. Larvae are V1-morphs, meaning mass is proportional to L**2 (Llandres&al)
        2. ratio of width to length constant :0.2. So area A = L*L*0.2.
        3. For this to give realistic values for both l1 (L=1.3mm) and l3 (L=5.2mm) we set
        density = 300 kg/m**2=0.3 mg/mm*2. (It is totally fortunate that box2d calculates mass as density*area)
        This yields m3=0.3 * 5.2*5.2*0.2  = 1.6224 mg and m1=0.3 * 1.3*1.3*0.2 = 0.1014 mg
        It follows that mass=density*width_to_length_ratio*length**2 for both real and simulated mass
        So, when using a scaling factor sf where sim_length=sf*real_length ==> sim_mass=sf**2 * real_mass'''

    def compute_mass_from_length(self):
        self.real_mass = self.density * self.real_length**2*self.width_to_length_ratio
        # self.sim_mass = self.density * self.sim_length**2*self.width_to_length_ratio

    def adjust_shape_to_mass(self):
        self.real_length = np.sqrt(self.real_mass/(self.density*self.width_to_length_ratio))

    def adjust_body_vertices(self):
        self.sim_length = self.real_length * self.model.scaling_factor
        self.seg_lengths = [self.sim_length * r for r in self.seg_ratio]
        l=self.sim_length / self.Nsegs
        self.seg_vertices = [v * l for v in self.base_seg_vertices]
        for i, seg in enumerate(self.segs):
            seg.seg_vertices=self.seg_vertices[i]

    # @property
    # def plot_vertices(self):
    #     return self.vertices.reshape((-1, 2))

    # @staticmethod
    # def _shape_vertices(self) -> np.ndarray:
    #     return self.real_length * self.generic_shape_vertices
    '''
    seg_vertices of 2 segments example :
    [array([[[ 0.5 ,  0.  ],
            [ 0.26,  0.2 ],
            [-0.5 ,  0.2 ],
            [-0.5 , -0.2 ],
            [ 0.26, -0.2 ],
            [ 0.5 , -0.  ]]]), 
    array([[[ 0.5 ,  0.2 ],
            [-0.34,  0.2 ],
            [-0.5 ,  0.1 ],
            [-0.5 , -0.1 ],
            [-0.34, -0.2 ],
            [ 0.5 , -0.2 ]]])]
    So first index defines number of segment, second is 0 by default, then we take max or min and then we get the x to couple it with 0.
    Prerequirement : All segments are drawn horizontally with front to the right and midline on x axis.
    '''

    def get_olfactor_position(self):
        # if self.physics_engine:
        #     return self.get_global_front_end_of_body()
        # else:
        #     new_pos = (self.pos[0] + math.cos(self.orientation) * self.get_sim_length() / 2,
        #                self.pos[1] + math.sin(self.orientation) * self.get_sim_length() / 2)
        #     return new_pos
        return self.get_global_front_end_of_head()

    def generate_segment_shapes(self, num_segments, width_to_length_proportion, density, interval, segment_ratio):
        shape_length = 1
        shape_width = width_to_length_proportion / 2
        front_end = 0.52
        front_max = 0.4
        front_length = front_end - front_max
        rear_max = -0.4
        rear_end = -0.48
        rear_length = rear_max - rear_end

        # generic larva shape with total lenth 1
        generic_shape = np.array([[(front_end, +0.0),
                                   (front_max, +shape_width * 2 / 3),
                                   (front_max / 3, +shape_width),
                                   (rear_max, +shape_width * 2 / 3),
                                   (rear_end, 0.0),
                                   (rear_max, -shape_width * 2 / 3),
                                   (front_max / 3, -shape_width),
                                   (front_max, -shape_width * 2 / 3)]])
        # generic_shape = np.array([[
        #                            (front_max, +shape_width),
        #                            (rear_max, +shape_width),
        #                            (rear_end, +shape_width / 2),
        #                            (rear_end, -shape_width / 2),
        #                            (rear_max, -shape_width),
        #                            (front_max, -shape_width)]])
        if num_segments == 1:
            return [generic_shape]
        else:
            # seg_length = 1 / Nsegs

            seg_starts = [front_end + r - cum_r for r, cum_r in zip(segment_ratio, np.cumsum(segment_ratio))]
            seg_meds = [front_end + r / 2 - cum_r for r, cum_r in zip(segment_ratio, np.cumsum(segment_ratio))]
            seg_stops = [front_end - cum_r for r, cum_r in zip(segment_ratio, np.cumsum(segment_ratio))]
            seg_starts, seg_stops = self.add_interval_between_segments(num_segments, density, interval, seg_starts,
                                                                       seg_stops)
            # print(seg_starts, seg_stops)
            segment_vertices = []
            for i, (start, med, stop) in enumerate(zip(seg_starts, seg_meds, seg_stops)):
                if start > front_max and stop >= front_max:
                    shape = np.array([[(start - med, +(front_end - start) / front_length * shape_width),
                                       (stop - med, +(front_end - stop) / front_length * shape_width),
                                       (stop - med, -(front_end - stop) / front_length * shape_width),
                                       (start - med, -(front_end - start) / front_length * shape_width)]])
                elif start > front_max > stop >= rear_max:
                    shape = np.array([[(start - med, +(front_end - start) / front_length * shape_width),
                                       (front_max - med, +shape_width),
                                       (stop - med, +shape_width),
                                       (stop - med, -shape_width),
                                       (front_max - med, -shape_width),
                                       (start - med, -(front_end - start) / front_length * shape_width)]])
                elif rear_max < start <= front_max and rear_max <= stop < front_max:
                    shape = np.array([[(start - med, +shape_width),
                                       (stop - med, +shape_width),
                                       (stop - med, -shape_width),
                                       (start - med, -shape_width)]])
                elif front_max >= start > rear_max >= stop:
                    shape = np.array([[(start - med, +shape_width),
                                       (rear_max - med, +shape_width),
                                       (stop - med, +((stop - rear_end) / rear_length + 1) * shape_width / 2),
                                       (stop - med, -((stop - rear_end) / rear_length + 1) * shape_width / 2),
                                       (rear_max - med, -shape_width),
                                       (start - med, -shape_width)]])
                elif rear_max >= start:
                    shape = np.array([[(start - med, +((start - rear_end) / rear_length + 1) * shape_width / 2),
                                       (stop - med, +((stop - rear_end) / rear_length + 1) * shape_width / 2),
                                       (stop - med, -((stop - rear_end) / rear_length + 1) * shape_width / 2),
                                       (start - med, -((start - rear_end) / rear_length + 1) * shape_width / 2)]])
                segment_vertices.append(shape * num_segments)
            return segment_vertices

    # To make peristalsis visible we try to leave some space between the segments.
    # We define an interval proportional to the length : int*l.
    # We subtract it from the front end of all segments except the first and from the rear end of all segments except the last.
    # For Npoints=n, in total we subtract 2*(n-1)*int*l in length.
    # For width_to_length_ratio=w2l, the area of the body without intervals is A=w2l*l*l
    # Subtracting the intervals, this translates to A'= (l-2*(n-1)*int*l) * w2l*l = (1-2*(n-1)*int)*A
    # To get the same mass, we will raise the density=d to d' accordingly : mass=d*A = d'*A' ==> d'=d/(1-2*(n-1)*int)
    def add_interval_between_segments(self, num_segments, density, interval, seg_starts, seg_stops):
        for i in range(1, len(seg_starts)):
            seg_starts[i] -= interval
        for i in range(len(seg_stops) - 1):
            seg_stops[i] += interval

        self.density = density / (1 - 2 * (num_segments - 1) * interval)

        return seg_starts, seg_stops
