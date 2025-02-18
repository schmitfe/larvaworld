import os

import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
from scipy.stats import *
import scipy.stats as st

from lib.aux import naming as nam


def fit_angular_params(d, fit_filepath=None, chunk_only=None, absolute=False,
                       save_to=None, save_as=None):
    if save_to is None:
        save_to = d.plot_dir
    if save_as is None :
        if absolute :
            save_as='angular_fit_abs.pdf'
        else :
            save_as = 'angular_fit.pdf'
    filepath = os.path.join(save_to, save_as)
    if chunk_only is not None:
        s = d.step_data.loc[d.step_data[nam.id(chunk_only)].dropna().index]
    else:
        s = d.step_data
    # s = d.step_data
    # TURNER PARAMETERS
    # -----------------------

    # The bend of the front-body (sum of half the angles) is the target for the turner calibration
    # The head reorientation velocity is the result of the turner calibration
    # if mode == 'experiment':
    #     # point = d.critical_spinepoint
    #
    #     ho = d.unwrapped_flag(d.orientation_flag(d.segments[0]))
    #     # act_r = 'non_rest_dur_fraction'
    #     # dst = d.dst_param(d.critical_spinepoint)
    # elif mode == 'simulation':
    #     # point = 'centroid'
    #     ho = d.orientation_flag('head')
    # b = 'front_half_bend'
    b = 'bend'
    bv = nam.vel(b)
    ba = nam.acc(b)
    # hb=d.angles[0]
    # hbv=d.vel_param(hb)
    # hba=d.acc_param(hb)
    # ho = d.orientation_flag('head')
    ho = 'front_orientation'
    hov = nam.vel(ho)
    hoa = nam.acc(ho)
    # hca = f'turn_{ho}'
    hca = f'turn_{nam.unwrap(ho)}'
    pars = [b, bv, ba, hov, hoa, hca]
    ranges = [150, 400, 5000, 400, 5000, 100]
    # print(pars)

    if fit_filepath is None:
        # These are the fits of a 100 larvae dataset

        fitted_distros = [{'t': (2.36, 0, 13)},
                          {'t': (1.71, 0, 32.1)},
                          {'t': (1.94, 0, 331)},
                          {'t': (1.54, 0, 26.6)},
                          {'t': (1.87, 0, 300)},
                          {'t': (0.965, 0, 5.33)}]
        target_stats = [0.006, 0.01, 0.01, 0.005, 0.005, 0.026]
    else:
        pars, fitted_distros, target_stats = d.load_fits(filepath=fit_filepath, selected_pars=pars)
        # print(pars)
    nbins = 500
    # ranges=[80,300,3200,300,3200]
    height = 0.05
    colors = ['g', 'r', 'b', 'r', 'b', 'g']
    # labels=['bend', 'bend velocity', 'bend acceleration', 'orientation velocity', 'orientation acceleration']
    labels = [r'$\theta_{b}$', r'$\dot{\theta}_{b}$', r'$\ddot{\theta}_{b}$', r'$\dot{\theta}_{or}$',
              r'$\ddot{\theta}_{or}$', r'$\theta_{turn}$']
    xlabels = ['angle $(deg)$', 'angular velocity $(deg/sec)$', 'angular acceleration, $(deg^2/sec)$',
               'angular velocity $(deg/sec)$', 'angular acceleration, $(deg^2/sec)$', 'angle $(deg)$']
    order = [2, 1, 0, 4, 3, 5]
    fits = []
    fig, axs = plt.subplots(2, 3, figsize=(18, 8), sharey=True)
    axs = axs.ravel()
    for i, (par, w, r, l, xl, j, col, target) in enumerate(
            zip(pars, fitted_distros, ranges, labels, xlabels, order, colors, target_stats)):
        # print(i,par)
        x = np.linspace(-r, r, nbins)
        data = s[par].dropna().values
        if absolute :
            data=np.abs(data)
        weights = np.ones_like(data) / float(len(data))
        axs[j].hist(data, bins=x, weights=weights, label=l, color=col, alpha=0.8)
        dist_name=list(w.keys())[0]
        dist_args=list(w.values())[0]
        dist = getattr(st, dist_name)

        if dist.shapes is None :
            dist_args_dict = dict(zip(['loc', 'scale'], dist_args))
        else :
        # elif len(dist.shapes)==1 :
            dist_args_dict = dict(zip([dist.shapes]+['loc', 'scale'], dist_args))
        # print(dist_name)
        # print(dist_args)
        # print(dist_args_dict)
        stat, pvalue = stats.kstest(data, dist_name, args=dist_args)
        # print(stat, pvalue)
        fits.append([par, stat, pvalue])
        print(f'Parameter {par} was fitted with stat : {stat} vs target stat : {target}')
        y = dist.rvs(size=100000, **dist_args_dict)
        n_weights = np.ones_like(y) / float(len(y))
        my_n, my_bins, my_patches = axs[j].hist(y, bins=x, weights=n_weights, alpha=0)
        axs[j].scatter(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, marker='.', c='k', s=40, alpha=0.6)
        axs[j].plot(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, c='k', linewidth=2, alpha=0.6)
        # axs[j].plot(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, c='k', linewidth=2, alpha=0.6,
        #             label=f'{dist_name} fit')

        # axs[i].hist(y, color='k',weights=weights,bins=x, label=f'{list(w.keys())[0]} dist')
        axs[j].legend(loc='upper right', fontsize=15)
        axs[j].set_xlabel(xl, fontsize=15)

        axs[j].set_ylim([0, height])
        if absolute :
            axs[j].set_xlim([0, r])
        else :
            axs[j].set_xlim([-r, r])
        # plt.xlim([-r,r])
        # break
    axs[0].set_ylabel('probability, $P$', fontsize=15)
    axs[3].set_ylabel('probability, $P$', fontsize=15)
    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.1, hspace=0.3)
    plt.savefig(filepath, dpi=300)
    print(f'Image saved as {filepath} !')
    return fits


def fit_endpoint_params(d, fit_filepath=None, save_to=None, save_as='endpoint_fit.pdf'):
    if save_to is None:
        save_to = d.plot_dir
    filepath = os.path.join(save_to, save_as)
    e = d.endpoint_data
    # TURNER PARAMETERS
    # -----------------------

    # The bend of the front-body (sum of half the angles) is the target for the turner calibration
    # The head reorientation velocity is the result of the turner calibration
    # if mode == 'experiment':
    # point = d.critical_spinepoint

    # act_r = 'non_rest_dur_fraction'
    #
    # elif mode == 'simulation':
    # point = 'centroid'
    point = d.point
    dst = 'distance'
    # dst = d.dst_param(point)
    v = 'velocity'
    # v = d.vel_param(point)
    a = 'acceleration'
    # a = d.acc_param(point)
    sv = nam.scal(v)
    sa = nam.scal(a)
    cum_dst = nam.cum(dst)
    cum_sdst = nam.cum(nam.scal(dst))

    # Stride related parameters. The scal-distance-per-stride is the result of the crawler calibration
    stride_flag = nam.max(sv)
    stride_d = nam.dst('stride')
    stride_sd = nam.scal(stride_d)
    f_crawler = nam.freq(sv)
    Nstrides = nam.num('stride')
    stride_ratio = nam.dur_ratio('stride')
    l = 'length'

    pars = [l, f_crawler,
            nam.mean(stride_d), nam.mean(stride_sd),
            Nstrides, stride_ratio,
            cum_dst, cum_sdst,
            nam.max('40sec_dispersion'), nam.scal(nam.max('40sec_dispersion')),
            nam.final('40sec_dispersion'), nam.scal(nam.final('40sec_dispersion')),
            'stride_reoccurence_rate','stride_reoccurence_rate',
            nam.mean('bend'), nam.mean(nam.vel('bend'))]
    ranges = [(2, 6), (0.6, 2.25),
              (0.4, 1.6), (0.1, 0.35),
              (100, 300), (0.3, 1.0),
              (0, 360), (0, 80),
              (0, 70), (0, 20),
              (0, 70), (0, 20),
              (0.5, 1.0),(0.5, 1.0),
              (-20.0, 20.0), (-8.0, 8.0)]
    # print(pars)

    if fit_filepath is None:
        # These are the fits of a 100 larvae dataset
        fitted_distros = [{'norm': (4.57, 0.54)},
                          {'norm': (1.44, 0.203)},
                          {'norm': (1.081, 0.128)},
                          {'norm': (0.239, 0.031)},
                          {'norm': (249.8, 36.4)},
                          {'norm': (55.1, 7.9)},
                          {'norm': (43.3, 16.2)},
                          {'norm': (9.65, 3.79)}, ]
        target_stats = [0.074, 0.087, 0.086, 0.084, 0.057, 0.048, 0.068, 0.094]
    else:
        pars, fitted_distros, target_stats = d.load_fits(filepath=fit_filepath, selected_pars=pars)
        # print(pars)
    fits = []

    labels = ['body length', 'stride frequency',
              'stride displacement', 'scal stride displacement',
              'num strides', 'crawling ratio',
              'displacement in 3 min', 'scal displacement in 3 min',
              'max dispersion in 40 sec', 'max scal dispersion in 40 sec',
              'dispersion in 40 sec', 'scal dispersion in 40 sec',
              'stride reoccurence rate','stride reoccurence rate',
              'mean bend angle', 'mean bend velocity']
    xlabels = ['length $(mm)$', 'frequency $(Hz)$',
               'distance $(mm)$', 'scal distance $(-)$',
               'counts $(-)$', 'time ratio $(-)$',
               'distance $(mm)$', 'scal distance $(-)$',
               'distance $(mm)$', 'scal distance $(-)$',
               'distance $(mm)$', 'scal distance $(-)$',
               'rate $(-)$','rate $(-)$',
               'angle $(deg)$', 'angular velocity $(deg/sec)$']
    nbins = 20
    height = 0.3
    fig, axs = plt.subplots(int(len(pars) / 2), 2, figsize=(15, int(5 * len(pars) / 2)), sharey=True)
    axs = axs.ravel()
    for i, (par, lab, xl, (rmin, rmax), w, target) in enumerate(
            zip(pars, labels, xlabels, ranges, fitted_distros, target_stats)):
        # print(par)
        data = e[par].dropna().values
        # rmin, rmax=np.min(data), np.max(data)
        x = np.linspace(rmin, rmax, nbins)
        # f = Fitter(data)
        # f.distributions = ['norm']
        # f.timeout = 200
        # f.fit()
        # w = f.get_best()
        # print(w)
        loc, scale = list(w.values())[0]
        stat, pvalue = stats.kstest(data, list(w.keys())[0], args=list(w.values())[0])
        fits.append([par, stat, pvalue])
        print(f'Parameter {par} was fitted with stat : {stat} vs target stat : {target}')
        y = norm.rvs(size=10000, loc=loc, scale=scale)
        n_weights = np.ones_like(y) / float(len(y))
        my_n, my_bins, my_patches = axs[i].hist(y, bins=x, weights=n_weights, alpha=0)
        axs[i].scatter(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, marker='o', c='k', s=40, alpha=0.6)
        axs[i].plot(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, alpha=0.6, c='k', linewidth=2,
                    label='norm fit')

        weights = np.ones_like(data) / float(len(data))
        axs[i].hist(data, bins=x, weights=weights, label=lab, color='b', alpha=0.6)
        axs[i].legend(loc='upper right', fontsize=12)
        axs[i].set_xlabel(xl, fontsize=12)
        axs[i].set_ylim([0, height])
    axs[0].set_ylabel('probability, $P$', fontsize=15)
    axs[2].set_ylabel('probability, $P$', fontsize=15)
    axs[4].set_ylabel('probability, $P$', fontsize=15)

    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.01, hspace=0.3)
    plt.savefig(filepath, dpi=300)
    print(f'Image saved as {filepath} !')
    return fits


def fit_bout_params(d, fit_filepath=None, save_to=None, save_as='bout_fit.pdf'):
    if save_to is None:
        save_to = os.path.join(d.plot_dir, 'plot_bouts')
    if not os.path.exists(save_to):
        os.makedirs(save_to)
    filepath = os.path.join(save_to, save_as)
    e = d.endpoint_data
    s = d.step_data

    pars = [nam.chain_counts_par('stride'), nam.dur(nam.non('stride')),
            nam.dur_ratio('stride'), nam.dur_ratio('non_stride'),
            nam.num('stride'), nam.num('non_stride'),
            nam.dur('rest'), nam.dur('activity'),
            nam.dur_ratio('rest'), nam.dur_ratio('activity'),
            nam.num('rest'), nam.num('activity')]
    ranges = [(1.0, 40.0), (0.0, 10.0),
              (0.0, 1.0), (0, 1.0),
              (0, 300), (0, 120),
              (0, 3), (0, 60),
              (0.0, 1.0), (0.0, 1.0),
              (0, 100), (0, 100)]
    # print(pars)

    if fit_filepath is None:
        # These are the fits of a 100 larvae dataset
        raise ValueError('Not implemented. Please provide fit file')
    else:
        pars, fitted_distros, target_stats = d.load_fits(filepath=fit_filepath, selected_pars=pars)
        # print(pars)
    fits = []

    labels = ['stride chains', 'stride-free bouts',
              'stride ratio', 'stride-free ratio',
              'num strides', 'num non-strides',
              'rest bouts', 'activity bouts',
              'rest ratio', 'activity ratio',
              'num rests', 'num activities']
    xlabels = ['length $(-)$', 'time $(sec)$',
               'time fraction $(-)$', 'time fraction $(-)$',
               'counts $(-)$', 'counts $(-)$',
               'time $(sec)$', 'time $(sec)$',
               'time fraction $(-)$', 'time fraction $(-)$',
               'counts $(-)$', 'counts $(-)$']
    nbins = 30
    height = 0.4
    fig, axs = plt.subplots(6, 2, figsize=(15, 30), sharey=True)
    axs = axs.ravel()
    for i, (par, lab, xl, (rmin, rmax), w, target) in enumerate(
            zip(pars, labels, xlabels, ranges, fitted_distros, target_stats)):
        print(par)
        try:
            data = e[par].dropna().values
        except:
            data = s[par].dropna().values
        # rmin, rmax=np.min(data), np.max(data)
        x = np.linspace(rmin, rmax, nbins)
        # f = Fitter(data)
        # f.distributions = ['norm']
        # f.timeout = 200
        # f.fit()
        # w = f.get_best()
        # print(w)
        args = list(w.values())[0]
        name = list(w.keys())[0]
        stat, pvalue = stats.kstest(data, name, args=args)
        fits.append([par, stat, pvalue])
        print(f'Parameter {par} was fitted with stat : {stat} vs target stat : {target}')
        distr = getattr(stats.distributions, name)
        y = distr.rvs(*args, size=10000)
        n_weights = np.ones_like(y) / float(len(y))
        my_n, my_bins, my_patches = axs[i].hist(y, bins=x, weights=n_weights, alpha=0)
        axs[i].scatter(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, marker='o', c='k', s=40, alpha=0.6)
        axs[i].plot(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, alpha=0.6, c='k', linewidth=2,
                    label=f'{name} fit')

        weights = np.ones_like(data) / float(len(data))
        axs[i].hist(data, bins=x, weights=weights, label=lab, color='b', alpha=0.6)
        axs[i].legend(loc='upper right', fontsize=12)
        axs[i].set_xlabel(xl, fontsize=12)
        axs[i].set_ylim([0, height])
    axs[0].set_ylabel('probability, $P$', fontsize=15)
    axs[2].set_ylabel('probability, $P$', fontsize=15)
    axs[4].set_ylabel('probability, $P$', fontsize=15)

    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.01, hspace=0.3)
    plt.savefig(filepath, dpi=300)
    print(f'Image saved as {filepath} !')
    return fits


def fit_crawl_params(d, target_point=None,fit_filepath=None, save_to=None, save_as='crawl_fit.pdf'):
    if save_to is None:
        save_to = d.plot_dir
    filepath = os.path.join(save_to, save_as)
    e = d.endpoint_data
    if target_point is None :
        target_point=d.point
    point=d.point
    # exp_dst = nam.dst(d.point)
    exp_dst = 'distance'
    # dst = nam.dst(d.point)
    dst = 'distance'
    exp_cum_sdst = nam.cum(nam.scal(exp_dst))
    cum_sdst = nam.cum(nam.scal(dst))
    Nstrides = nam.num('stride')
    stride_ratio = nam.dur_ratio('stride')
    dispersion = nam.scal(nam.final('40sec_dispersion'))

    exp_pars = [Nstrides, stride_ratio, exp_cum_sdst]
    pars = [Nstrides, stride_ratio, cum_sdst]
    ranges = [(100, 300), (0.5, 1.0),(20, 80)]
    # print(pars)
    # print(exp_cum_sdst, cum_sdst)
    exp_pars, fitted_distros, target_stats = d.load_fits(filepath=fit_filepath, selected_pars=exp_pars)
    # print(exp_pars)
    fits = []

    labels = ['$N_{strides}$', 'crawling ratio',
              '$distance_{scal}$']
    xlabels = ['counts $(-)$', 'time ratio $(-)$',
               'scal distance $(-)$']
    colors = ['r', 'c', 'g']
    nbins = 20
    height = 0.3
    fig, axs = plt.subplots(int(len(pars) / 3), 3, figsize=(15, int(5 * len(pars) / 3)), sharey=True)
    axs = axs.ravel()
    for i, (par, lab, xl, (rmin, rmax), w, target, c) in enumerate(
            zip(pars, labels, xlabels, ranges, fitted_distros, target_stats, colors)):
        # print(par)
        data = e[par].dropna().values
        # rmin, rmax=np.min(data), np.max(data)
        x = np.linspace(rmin, rmax, nbins)
        # f = Fitter(data)
        # f.distributions = ['norm']
        # f.timeout = 200
        # f.fit()
        # w = f.get_best()
        # print(w)
        loc, scale = list(w.values())[0]
        stat, pvalue = stats.kstest(data, list(w.keys())[0], args=list(w.values())[0])
        fits.append([par, stat, pvalue])
        print(f'Parameter {par} was fitted with stat : {stat} vs target stat : {target}')
        y = norm.rvs(size=10000, loc=loc, scale=scale)
        n_weights = np.ones_like(y) / float(len(y))
        my_n, my_bins, my_patches = axs[i].hist(y, bins=x, weights=n_weights, alpha=0)
        axs[i].scatter(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, marker='o', c='k', s=40, alpha=0.6)
        axs[i].plot(my_bins[:-1] + 0.5 * (my_bins[1:] - my_bins[:-1]), my_n, alpha=0.6, c='k', linewidth=2)

        weights = np.ones_like(data) / float(len(data))
        axs[i].hist(data, bins=x, weights=weights, label=lab, color=c, alpha=0.6)
        axs[i].legend(loc='upper right', fontsize=12)
        axs[i].set_xlabel(xl, fontsize=12)
        axs[i].set_ylim([0, height])
    axs[0].set_ylabel('probability, $P$', fontsize=15)

    plt.subplots_adjust(left=0.05, bottom=0.1, right=0.99, top=0.95, wspace=0.01, hspace=0.3)
    plt.savefig(filepath, dpi=300)
    print(f'Image saved as {filepath} !')
    return fits


def powerlaw_cdf(x, durmin, alpha):
    return 1 - (x / durmin) ** (1 - alpha)


def powerlaw_pdf(x, durmin, alpha):
    return (alpha - 1) / durmin * (x / durmin) ** (-alpha)


def exponential_cdf(x, durmin, beta):
    return 1 - np.exp(-beta * (x - durmin))


def exponential_pdf(x, durmin, beta):
    return beta * np.exp(-beta * (x - durmin))


def lognormal_cdf(x, mu, sigma):
    return 0.5 + 0.5 * sp.special.erf((np.log(x) - mu) / np.sqrt(2) / sigma)


def lognormal_pdf(x, mu, sigma):
    return 1 / (x * sigma * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((np.log(x) - mu) / sigma) ** 2)


def compute_density(x, xmin, xmax, Nbins=64):
    log_range = np.linspace(np.log2(xmin), np.log2(xmax), Nbins)
    bins = np.unique((2 * 2 ** (log_range)) / 2)
    x_filt = x[x >= xmin]
    x_filt = x_filt[x_filt <= xmax]
    cdf = np.ones(len(bins))
    pdf = np.zeros(len(bins) -1)
    for i in range(len(bins)):
        cdf[i] = 1 - np.mean(x_filt < bins[i])
        if i >= 1:
            pdf[i - 1] = -(cdf[i] - cdf[i - 1]) / (bins[i] - bins[i - 1])
    return bins, pdf, cdf


def analyse_bouts(dataset, parameter, scale_coef=1, label=None, xlabel=r'time$(sec)$',
                  dur_max_in_std=None, dur_range=None, save_as=None, save_to=None) :
    if label is None :
        label=parameter
    if save_as is None :
        save_as=f'{label}_bouts.pdf'
    if save_to is None :
        save_to=os.path.join(dataset.plot_dir, 'plot_bouts')
    if not os.path.exists(save_to):
        os.makedirs(save_to)
    filepath=os.path.join(save_to, save_as)

    s=dataset.step_data
    fig, axs = plt.subplots(1, 2, figsize=(10, 5), sharex=True, sharey=True)
    axs = axs.ravel()
    dur = s[parameter].dropna().values*scale_coef
    if dur_range is None :
        if dur_max_in_std is None :
            # durmin, durmax = 1, np.max(dur)
            durmin, durmax = np.min(dur), np.max(dur)
            print(durmin, durmax)
        else :
            std=np.std(dur)
            m=np.mean(dur)
            durmin, durmax = np.min(dur),m+dur_max_in_std*std
    else :
        durmin, durmax =dur_range

    dur = dur[dur >= durmin]
    dur = dur[dur <= durmax]
    u2, c2, c2cum = compute_density(dur, durmin, durmax)
    du2 = 0.5 * (u2[:-1] + u2[1:])
    print(len(u2), len(du2), len(u2))
    print(durmin, durmax)
    alpha = 1 + len(dur) / np.sum(np.log(dur / durmin))
    print("powerlaw exponent MLE:", alpha)

    beta = len(dur) / np.sum(dur - durmin)
    print("exponential exponent MLE:", beta)

    mean_lognormal = np.mean(np.log(dur))
    std_lognormal = np.std(np.log(dur))
    print("lognormal mean,std:", mean_lognormal, std_lognormal)

    KS_plaw = np.max(np.abs(c2cum - 1 + powerlaw_cdf(u2, durmin, alpha)))
    KS_exp = np.max(np.abs(c2cum - 1 + exponential_cdf(u2, durmin, beta)))
    KS_logn = np.max(np.abs(c2cum - 1 + lognormal_cdf(u2, mean_lognormal, std_lognormal)))
    print()
    print('KS plaw', KS_plaw)
    print('KS exp', KS_exp)
    print('KS logn', KS_logn)

    idx_max=np.argmin([KS_plaw,KS_exp,KS_logn])
    lws=[2,2,2]
    lws[idx_max]=4

    # axs[i].loglog(u1, c1, 'or', label=name)
    axs[0].loglog(du2, c2, 'or', label=label)
    axs[0].loglog(du2, powerlaw_pdf(du2, durmin, alpha), 'r', lw=lws[0], label='powerlaw MLE')
    axs[0].loglog(du2, exponential_pdf(du2, durmin, beta), 'g', lw=lws[1], label='exponential MLE')
    axs[0].loglog(du2, lognormal_pdf(du2, mean_lognormal, std_lognormal), 'b', lw=lws[2], label='lognormal MLE')

    axs[0].legend(loc='lower left', fontsize=15)
    axs[0].axis([durmin, durmax, 1E-5, 1E-0])

    axs[1].loglog(u2, c2cum, 'or', label=label)
    axs[1].loglog(u2, 1 - powerlaw_cdf(u2, durmin, alpha), 'r', lw=lws[0], label='powerlaw MLE')
    axs[1].loglog(u2, 1 - exponential_cdf(u2, durmin, beta), 'g', lw=lws[1], label='exponential MLE')
    axs[1].loglog(u2, 1 - lognormal_cdf(u2, mean_lognormal, std_lognormal), 'b', lw=lws[2], label='lognormal MLE')

    axs[1].legend(loc='lower left', fontsize=15)
    # axs[1].axis([1.1*durmin, 1.1*durmax,1E-2,1.1*1E-0])
    axs[0].set_title('pdf', fontsize=20)
    axs[1].set_title('cdf', fontsize=20)
    axs[0].set_ylabel('probability', fontsize=15)
    axs[0].set_xlabel(xlabel, fontsize=15)
    axs[1].set_xlabel(xlabel, fontsize=15)
    # axs[i].text(25, 10 ** - 1.5, r'$\alpha=' + str(np.round(alpha * 100) / 100) + '$',
    #        {'color': 'k', 'fontsize': 16})
    # fig.text(0.5, 0.04, r'Duration, $d$', ha='center',fontsize=30)
    # fig.text(0.04, 0.5, r'Cumulative density function, $P_\theta(d)$', va='center', rotation='vertical',fontsize=30)
    fig.subplots_adjust(top=0.92, bottom=0.15, left=0.1, right=0.95, hspace=.005, wspace=0.005)
    fig.savefig(filepath, dpi=300)
    print(f'Plot saved as {filepath}.')