import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from math import ceil
import gropt


def get2_eddy_mode0(G, lam, dt):
    E0 = np.zeros_like(G)
    for i in range(G.size):
        ii = float(G.size - i - 1)
        if i == 0:
            val = -np.exp(-ii*dt/lam)
        else:
            val = np.exp(-(ii+1.0)*dt/lam) - np.exp(-ii*dt/lam)
        E0[i] = -val
    
    return E0

def get2_eddy_mode1(G, lam, dt):
    E1 = np.zeros_like(G)
    
    val = 0.0
    for i in range(G.size):
        ii = float(G.size - i - 1)
        val += -np.exp(-ii*dt/lam)
    E1[0] = val * 1e3 * dt
    
    for i in range(1, G.size):
        ii = float(G.size - i)
        val = -np.exp(-ii*dt/lam)
        E1[i] = val  * 1e3 * dt
    
    return E1


def get_eddy_curves(G, dt, max_lam, n_lam):
    all_lam = np.linspace(1e-4, max_lam, n_lam)
    all_e0 = []
    all_e1 = []
    for lam in all_lam:
        lam = lam * 1.0e-3

        E0 = get2_eddy_mode0(G, lam, dt)
        all_e0.append(np.sum(E0*G))

        E1 = get2_eddy_mode1(G, lam, dt)
        all_e1.append(np.sum(E1*G))

    return all_lam, all_e0, all_e1

def get_min_TE(params, bval = 1000, min_TE = -1, max_TE = -1, verbose = 0):
    if params['mode'][:4] == 'diff':
        if min_TE < 0:
            min_TE = params['T_readout'] + params['T_90'] + params['T_180'] + 10
        
        if max_TE < 0:
            max_TE = 200

        G_out, T_out = get_min_TE_diff(params, bval, min_TE, max_TE, verbose)

    elif params['mode'] == 'free':
        if min_TE < 0:
            min_TE = 0.1
        
        if max_TE < 0:
            max_TE = 5.0

        G_out, T_out = get_min_TE_free(params, min_TE, max_TE, verbose)
    
    return G_out, T_out


def get_min_TE_diff(params, target_bval, min_TE, max_TE, verbose = 0):
    
    T_lo = min_TE
    T_hi = max_TE
    T_range = T_hi-T_lo

    best_time = 999999.9

    if 'dt' in params:
        dt = params['dt']
    else:
        dt = 1.0e-3/params['N0']

    if verbose:
        print('Testing TE =', end='', flush=True)
    while ((T_range*1e-3) > (dt/4.0)): 
        params['TE'] = T_lo + (T_range)/2.0
        if verbose:
            print(' %.3f' % params['TE'], end='', flush=True)
        G, ddebug = gropt.gropt(params)
        lim_break = ddebug[14]
        bval = get_bval(G, params)
        if bval > target_bval:
            T_hi = params['TE']
            if T_hi < best_time:
                G_out = G
                T_out = T_hi
                best_time = T_hi
        else:
            T_lo = params['TE']
        T_range = T_hi-T_lo

    if verbose:
        print(' Final TE = %.3f ms' % T_out)

    params['TE'] = T_out
    return G_out, T_out

def get_min_TE_free(params, min_TE, max_TE, verbose = 0):
    
    T_lo = min_TE
    T_hi = max_TE
    T_range = T_hi-T_lo

    best_time = 999999.9

    if 'dt' in params:
        dt = params['dt']
    else:
        dt = 1.0e-3/params['N0']

    if verbose:
        print('Testing TE =', end='', flush=True)
    while ((T_range*1e-3) > (dt/4.0)): 
        params['TE'] = T_lo + (T_range)/2.0
        if verbose:
            print(' %.3f' % params['TE'], end='', flush=True)
        G, ddebug = gropt.gropt(params)
        lim_break = ddebug[14]
        if lim_break == 0:
            T_hi = params['TE']
            if T_hi < best_time:
                G_out = G
                T_out = T_hi
                best_time = T_hi
        else:
            T_lo = params['TE']
        T_range = T_hi-T_lo

    if verbose:
        print(' Final TE = %.3f ms' % T_out)

    return G_out, T_out



def get_stim(G, dt):
    alpha = 0.333
    r = 23.4
    c = 334e-6
    Smin = r/alpha
    coeff = []
    for i in range(G.size):
        coeff.append( c / ((c + dt*(G.size-1) - dt*i)**2.0) / Smin )
    coeff = np.array(coeff)

    stim_out = []
    for j in range(G.size-1):
        ss = 0
        for i in range(j+1):
            ss += coeff[coeff.size-1-j+i]*(G[i+1]-G[i])
        stim_out.append(ss)

    stim_out = np.array(stim_out)
    return stim_out

def get_moments(G, T_readout, dt):
    TE = G.size*dt*1e3 + T_readout
    tINV = int(np.floor(TE/dt/1.0e3/2.0))
    GAMMA   = 42.58e3; 
    INV = np.ones(G.size)
    INV[tINV:] = -1
    Nm = 5
    tvec = np.arange(G.size)*dt
    tMat = np.zeros((Nm, G.size))
    scaler = np.zeros(Nm)
    for mm in range(Nm):
        tMat[mm] = tvec**mm
        scaler[mm] = (dt*1e3)**mm
                                 
    moments = np.abs(GAMMA*dt*tMat@(G*INV))
    return moments

def get_bval(G, params):

    TE = params['TE']
    T_readout = params['T_readout']
    dt = (TE-T_readout) * 1.0e-3 / G.size
    
    tINV = int(np.floor(TE/dt/1.0e3/2.0))
    GAMMA   = 42.58e3; 
    
    INV = np.ones(G.size)
    INV[tINV:] = -1
    
    Gt = 0
    bval = 0
    for i in range(G.size):
        if i < tINV:
            Gt += G[i] * dt
        else:
            Gt -= G[i] * dt
        bval += Gt*Gt*dt

    bval *= (GAMMA*2*np.pi)**2
    
    return bval

def plot_moments(G, T_readout, dt):

    TE = G.size*dt*1e3 + T_readout
    tINV = int(np.floor(TE/dt/1.0e3/2.0))
    GAMMA   = 42.58e3; 
    INV = np.ones(G.size)
    INV[tINV:] = -1
    Nm = 5
    tvec = np.arange(G.size)*dt
    tMat = np.zeros((Nm, G.size))
    for mm in range(Nm):
        tMat[mm] = tvec**mm

    moments = np.abs(GAMMA*dt*tMat@(G*INV))
    mm = GAMMA*dt*tMat * (G*INV)[np.newaxis,:]

    plt.figure()
    mmt = np.cumsum(mm[0])
    plt.plot(mmt/np.abs(mmt).max())
    mmt = np.cumsum(mm[1])
    plt.plot(mmt/np.abs(mmt).max())
    mmt = np.cumsum(mm[2])
    plt.plot(mmt/np.abs(mmt).max())
    plt.axhline(0, color='k')


def get_moment_plots(G, T_readout, dt, diffmode = 1):

    TE = G.size*dt*1e3 + T_readout
    tINV = int(np.floor(TE/dt/1.0e3/2.0))
    GAMMA   = 42.58e3; 
    INV = np.ones(G.size)
    if diffmode > 0:
        INV[tINV:] = -1
    Nm = 5
    tvec = np.arange(G.size)*dt
    tMat = np.zeros((Nm, G.size))
    for mm in range(Nm):
        tMat[mm] = tvec**mm

    moments = np.abs(GAMMA*dt*tMat@(G*INV))
    mm = GAMMA*dt*tMat * (G*INV)[np.newaxis,:]

    out = []
    for i in range(Nm):
        mmt = np.cumsum(mm[i])
        out.append(mmt)

    return out

def plot_waveform(G, params, plot_moments = True, plot_eddy = True, plot_pns = True, plot_slew = True,
                  suptitle = '', eddy_lines=[], eddy_range = [1e-3,120,1000]):
    sns.set()
    sns.set_context("talk")
    
    TE = params['TE']
    T_readout = params['T_readout']
    diffmode = 0
    if params['mode'][:4] == 'diff':
        diffmode = 1

    dt = (TE-T_readout) * 1.0e-3 / G.size
    tt = np.arange(G.size) * dt * 1e3
    tINV = TE/2.0
    
    N_plots = 1
    if plot_moments: 
        N_plots += 1
    if plot_eddy: 
        N_plots += 1
    if plot_pns: 
        N_plots += 1
    if plot_slew: 
        N_plots += 1

    N_rows = 1 + (N_plots-1)//3
    N_cols = ceil(N_plots/N_rows)

    f, axarr = plt.subplots(N_rows, N_cols, squeeze=False, figsize=(12, N_rows*3.5))
    
    i_row = 0
    i_col = 0

    bval = get_bval(G, params)
    blabel = '    bval = %.0f' % bval
    if suptitle:
        f.suptitle(suptitle + blabel)
    elif diffmode > 0:
        f.suptitle(blabel)
        
    if diffmode > 1:
        axarr[i_row, i_col].axvline(tINV, linestyle='--', color='0.7')
    axarr[i_row, i_col].plot(tt, G*1000)
    axarr[i_row, i_col].set_title('Gradient')
    axarr[i_row, i_col].set_xlabel('t [ms]')
#     axarr[i_row, i_col].set_ylabel('G [mT/m]')
    i_col += 1
    if i_col >= N_cols:
        i_col = 0
        i_row += 1

    if plot_slew:
        axarr[i_row, i_col].plot(tt[:-1], np.diff(G)/dt)
        axarr[i_row, i_col].set_title('Slew')
        axarr[i_row, i_col].set_xlabel('t [ms]')

        i_col += 1
        if i_col >= N_cols:
            i_col = 0
            i_row += 1



    if plot_moments:
        mm = get_moment_plots(G, T_readout, (TE-T_readout) * 1.0e-3 / G.size, diffmode)
        axarr[i_row, i_col].axhline(linestyle='--', color='0.7')
        for i in range(3):
            mmt = mm[i]
            axarr[i_row, i_col].plot(tt, mmt/np.abs(mmt).max())
        axarr[i_row, i_col].set_title('Moments')
        axarr[i_row, i_col].set_xlabel('t [ms]')
    #     axarr[i_row, i_col].set_ylabel('Moment [AU]')
        i_col += 1
        if i_col >= N_cols:
            i_col = 0
            i_row += 1


    if plot_eddy:
        all_lam = np.linspace(eddy_range[0],eddy_range[1],eddy_range[2])
        all_e = []
        for lam in all_lam:
            lam = lam * 1.0e-3
            r = np.diff(np.exp(-np.arange(G.size+1)*dt/lam))[::-1]
            all_e.append(100*r@G)
        
        
        for e in eddy_lines:
            axarr[i_row, i_col].axvline(e, linestyle=':', color=(0.8, 0.1, 0.1, 0.8))
        
        axarr[i_row, i_col].axhline(linestyle='--', color='0.7')
        axarr[i_row, i_col].plot(all_lam, all_e)
        axarr[i_row, i_col].set_title('Eddy')
        axarr[i_row, i_col].set_xlabel('lam [ms]')
    #     axarr[i_row, i_col].set_ylabel(' [AU]')
        i_col += 1
        if i_col >= N_cols:
            i_col = 0
            i_row += 1


    if plot_pns:
        pns = np.abs(get_stim(G, dt))

        axarr[i_row, i_col].axhline(1.0, linestyle=':', color=(0.8, 0.1, 0.1, 0.8))
        
        axarr[i_row, i_col].axhline(linestyle='--', color='0.7')
        axarr[i_row, i_col].plot(tt[:-1], pns)
        axarr[i_row, i_col].set_title('PNS')
        axarr[i_row, i_col].set_xlabel('t [ms]')
        i_col += 1
        if i_col >= N_cols:
            i_col = 0
            i_row += 1

    plt.tight_layout(w_pad=0.0, rect=[0, 0.03, 1, 0.95])