#!/usr/bin/env python
# !/usr/bin/env python
import copy
import PySimpleGUI as sg
import matplotlib
from tkinter import *

from lib.gui.analysis_tab import build_analysis_tab, eval_analysis
from lib.gui.gui_lib import SYMBOL_DOWN, SYMBOL_UP, on_image, off_image
from lib.gui.model_tab import build_model_tab, eval_model
from lib.gui.simulation_tab import build_sim_tab, eval_sim

sys.path.insert(0, '..')

from lib.conf import exp_types, test_larva, agent_pars, test_env, odor_gain_pars

from lib.sim.single_run import run_sim, next_idx, configure_sim


matplotlib.use('TkAgg')
sg.theme('LightGreen')


def run_gui():
    collapsibles={}
    l_anal, graph_dict, data, func, func_kwargs, fig, save_to, save_as, figure_agg = build_analysis_tab()
    l_sim, sim_datasets, collapsibles, output_keys, source_units, border_list, larva_groups, source_groups = build_sim_tab(collapsibles)
    l_mod, collapsibles, module_keys, odor_gains = build_model_tab(collapsibles)

    l_gui = [
        [sg.TabGroup([[
            sg.Tab('Model', l_mod, background_color='darkseagreen', key='MODEL_TAB'),
            sg.Tab('Simulation', l_sim, background_color='darkseagreen', key='SIMULATION_TAB'),
            sg.Tab('Analysis', l_anal, background_color='darkseagreen', key='ANALYSIS_TAB')]],
            key='ACTIVE_TAB', tab_location='top', selected_title_color='purple')]
    ]

    w = sg.Window('Larvaworld gui', l_gui, resizable=True, finalize=True, size=(2000, 1200))

    while True:
        e, v = w.read()
        if e in (None, 'Exit'):
            break
        if e.startswith('OPEN SEC'):
            sec_name = e.split()[-1]
            if collapsibles[sec_name].state is not None:
                collapsibles[sec_name].state = not collapsibles[sec_name].state
                w[e].update(SYMBOL_DOWN if collapsibles[sec_name].state else SYMBOL_UP)
                w[f'SEC {sec_name}'].update(visible=collapsibles[sec_name].state)
        elif 'TOGGLE' in e:
            if w[e].metadata.state is not None:
                w[e].metadata.state = not w[e].metadata.state
                w[e].update(image_data=on_image if w[e].metadata.state else off_image)

        tab = v['ACTIVE_TAB']
        if tab == 'ANALYSIS_TAB':
            w, func, func_kwargs, data, figure_agg, fig, save_to, save_as = eval_analysis(e, v, w,
                                                                                          func, func_kwargs, data,
                                                                                          figure_agg, fig, save_to,
                                                                                          save_as, graph_dict)
        elif tab == 'MODEL_TAB':
            odor_gains = eval_model(e, v, w, collapsibles, module_keys,odor_gains)
        elif tab == 'SIMULATION_TAB':
            source_units, border_list, larva_groups, source_groups = eval_sim(e, v, w, sim_datasets, collapsibles, output_keys, source_units, border_list, larva_groups, source_groups)
    w.close()
    return


if __name__ == "__main__":
    run_gui()
