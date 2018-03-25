#!python3.6.3
import logging
import os
import sys
import math
import numpy as np
from scipy.interpolate import interp2d
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mpl_toolkits.mplot3d import Axes3D
from multiprocessing import Process

#matplotlib.rcParams['toolbar'] = 'None'
cmap_standard = plt.cm.get_cmap('RdYlBu')

#TODO: save .csv file of data when 'save' is True
#TODO: add black default color scheme
#TODO: add linetype and dottype to 2D plot
#TODO: add custom ticks to 2D plot
#TODO: add gridlines more generally

def getProjection(plotclass):
    if hasattr(plotclass, 'projection'):
        if plotclass.projection == '3d':
            return '3d'
    return None

def combinePlotsAndSave(plotclasses, destname='', grid=None, aspects=None,
                        save=False, show=True):
    args_tuple = tuple(reversed(list(locals().values())))  # original locals() is in reversed order]
    Process(target=combinePlotsAndSaveProcess, args=args_tuple).start()

def combinePlotsAndSaveProcess(plotclasses, destname='', grid=None, aspects=None,
                        save=False, show=True):
    n = len(plotclasses)
    fig = plt.figure(facecolor='white', edgecolor='white')
    fig.canvas.set_window_title('')
    axs = [None]*n
    gridx, gridy = grid[1], grid[0] #first is y then x then number of plot
    #in grid pattern
    for i in range(n):
        axs[i] = fig.add_subplot(gridx, gridy, i+1, projection=getProjection(plotclasses[i]))
        axs[i] = plotclasses[i].getPlot(axs[i])
        if plotclasses[i].legend: lgd = axs[i].legend(loc=plotclasses[i].legend_loc)
        xmin, xmax = axs[i].get_xlim()
        ymin, ymax = axs[i].get_ylim()
        aspect = 1
        if type(aspects) is list and len(aspects) >= n: aspect = aspects[i]
        axs[i].set_aspect(abs((xmax - xmin) / (ymax - ymin)) * aspect, adjustable='box-forced')

    fig.tight_layout()
    if save:
        fig.savefig(destname, bbox_inches='tight')
    if show:
        plt.show()
        plt.close()
    return fig, axs

def singlePlotAndSave(plotclass, destname='',
                      save=False, show=True):
    args_tuple = tuple(reversed(list(locals().values()))) #original locals() is in reversed order]
    Process(target=singlePlotAndSaveProcess, args=args_tuple).start()

def singlePlotAndSaveProcess(plotclass, destname='',
                      save=False, show=True):
    fig = plt.figure(facecolor='white')
    fig.canvas.set_window_title('')
    ax = fig.add_subplot(111, projection=getProjection(plotclass))
    ax = plotclass.getPlot(ax)
    #legend
    lgd = None
    if plotclass.legend: lgd = ax.legend(loc=plotclass.legend_loc)
    #save and show
    if save:
        if lgd is None: fig.savefig(destname, bbox_inches='tight')
        else:
            fig.savefig(destname, bbox_extra_artists=(lgd,), bbox_inches='tight')
    if show:
        plt.show()
        plt.close()
    return fig, ax

def addLabels(ax, titlename, label_x, label_y):
    ax.set_title(titlename)
    ax.set_xlabel(label_x)
    ax.set_ylabel(label_y)
    return ax

def addLimitsXY(ax, range_x, range_y):
    if range_x is not None:
        ax.set_xlim(*range_x)
    if range_y is not None:
        ax.set_ylim(*range_y)
    return ax

class plot2D:
    def __init__(self, data=None, range_x=None, range_y=None, logx=False, logy=False,
                 titlename='', label_x='x', label_y='y',
                 legend=True, legend_loc='upper right', xformat='normal'):
        #DATA INPUT: single dict OR list of dicts
        #essential keys: 'x', 'y' | optional keys: 'label', 'xerr', 'yerr'
        self.data = data
        self.range_x = range_x
        self.range_y = range_y
        self.logx = logx
        self.logy = logy
        self.titlename = titlename
        self.label_x = label_x
        self.label_y = label_y
        self.legend = legend
        self.legend_loc = legend_loc
        self.xformat = xformat

    def getPlot(self, ax):
        #test if data has the right structure
        if type(self.data) is dict:
            self.data = [self.data]
        elif not type(list):
            raise Exception('data is not (list of) dictionary(s)')

        for d in self.data:
            if 'label' not in d: d['label'] = ' '
            if 'linestyle' not in d: d['linestyle'] = '-'
            if not any(k in d for k in ('xerr', 'yerr')):
                # normal plot
                ax.plot(d['x'], d['y'], d['linestyle'], label=d['label'])
            else:
                # plot with errorbars
                if not 'xerr' in d: d['xerr'] = 0
                if not 'yerr' in d: d['yerr'] = 0
                ax.errorbar(d['x'], d['y'], d['linestyle'],
                            xerr=d['xerr'], yerr=d['yerr'], label=d['label'],
                            capsize=3)
        #add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax = addLimitsXY(ax, self.range_x, self.range_y)
        ax.grid(linestyle='--')
        if self.xformat=='date':
            ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
        if self.logx:
            ax.set_xscale('log', nonposx='clip')
        if self.logy:
            ax.set_yscale('log', nonposy='clip')
        return ax

class plotHist:
    def __init__(self, data=None, range_x=None, range_y=None,
                 titlename='', label_x='x', label_y='y',
                 legend=True, legend_loc='upper right'):
        #DATA INPUT: single dict OR list of dicts
        #essential keys: 'x', 'binsize' | optional keys: 'label'
        self.data = data
        self.range_x = range_x
        self.range_y = range_y
        self.titlename = titlename
        self.label_x = label_x
        self.label_y = label_y
        self.legend = legend
        self.legend_loc = legend_loc

    def getPlot(self, ax):
        #test if data has the right structure
        if type(self.data) is dict:
            self.data = [self.data]
        elif not type(list):
            raise Exception('data is not (list of) dictionary(s)')

        for d in self.data:
            if 'normed' not in d: d['normed'] = None
            if 'alpha' not in d: d['alpha'] = 1
            if 'label' not in d: d['label'] = ' '
            ax.hist(d['x'], d['bins'], normed=d['normed'], alpha=d['alpha'], label=d['label'])
        #add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax = addLimitsXY(ax, self.range_x, self.range_y)
        ax.grid()
        return ax

class plotBar:
    def __init__(self, data=None, range_y=None,
                 titlename='', label_x='x', label_y='y',
                 legend=True, legend_loc='upper right'):
        #DATA INPUT: single dict OR list of dicts
        #essential keys: 'x', 'labels' | optional keys: 'yerr', 'label'
        self.data = data
        self.range_y = range_y
        self.titlename = titlename
        self.label_x = label_x
        self.label_y = label_y
        self.legend = legend
        self.legend_loc = legend_loc

    def getPlot(self, ax):
        #test if data has the right structure
        if type(self.data) is dict:
            self.data = [self.data]
        elif not type(list):
            raise Exception('data is not (list of) dictionary(s)')

        gap=0.2
        barwidth = (1-gap)/len(self.data) #1 barwidth is touching bars
        pos = 0
        ind = np.arange(len(self.data[0]['labels']))
        for d in self.data:
            if 'yerr' not in d: d['yerr'] = None
            if 'label' not in d: d['label'] = ' '
            ax.bar(pos+ind, d['x'], barwidth, label=d['label'], yerr=d['yerr'], capsize=3)
            pos += barwidth
        ax.set_xticks( 1/2*(2*ind-barwidth +1-gap))
        ax.set_xticklabels(self.data[0]['labels'])
        #add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax = addLimitsXY(ax, None, self.range_y)
        ax.grid()
        return ax

class plot3D:
    def __init__(self, data=None, range_x=None, range_y=None, range_z=None,
                 titlename='', label_x='x', label_y='y', label_z='z',
                 legend=True, legend_loc='upper right'):
        #DATA INPUT: single dict OR list of dicts
        #essential keys: 'x', 'y', 'z' | optional keys: 'label', 'surftype'
        self.data = data
        self.range_x = range_x
        self.range_y = range_y
        self.range_z = range_z
        self.titlename = titlename
        self.label_x = label_x
        self.label_y = label_y
        self.label_z = label_z
        self.legend = legend
        self.legend_loc = legend_loc
        self.projection = '3d'

    def getPlot(self, ax):
        #test if data has the right structure
        if type(self.data) is dict:
            self.data = [self.data]
        elif not type(list):
            raise Exception('data is not (list of) dictionary(s)')

        for d in self.data:
            if 'label' not in d: d['label'] = ' '
            if 'surftype' not in d or d['surftype'] == 'scatter':
                ax.scatter(d['x'], d['y'], d['z'], label=d['label'])
            elif d['surftype'] == 'trisurf':
                ax.plot_trisurf(d['x'], d['y'], d['z'], cmap=cmap_standard) #label not possible

        #add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax.set_zlabel(self.label_z)
        ax = addLimitsXY(ax, self.range_x, self.range_y)
        if self.range_z is not None:
            ax.set_zlim(*self.range_z)

        #ax.view_init(0, 45)
        ax.w_xaxis.set_pane_color((1, 1, 1))
        ax.w_yaxis.set_pane_color((1, 1, 1))
        ax.w_zaxis.set_pane_color((1, 1, 1))
        return ax

class plotMap:
    def __init__(self, data=None, range_x=None, range_y=None, range_z=None,
                 titlename='', label_x='x', label_y='y', label_z='z',
                 interpnumber=10):
    # DATA INPUT: single dict NOT list of dicts
    # essential keys: 'x', 'y', 'z' | optional keys: None
        self.data = data
        self.range_x = range_x
        self.range_y = range_y
        self.range_z = range_z
        self.titlename = titlename
        self.label_x = label_x
        self.label_y = label_y
        self.label_z = label_z
        self.legend = False
        self.legend_loc = None
        self.interpnumber = interpnumber

    def getPlot(self, ax):
        # test if data has the right structure
        if type(self.data) is not dict:
            raise Exception('data is not (list of) dictionary(s)')
        limits_z = [min(self.data['z']), max(self.data['z'])]
        if self.range_z is not None:
            limits_z = self.range_z
        cax = ax.tricontourf(self.data['x'], self.data['y'], self.data['z'], self.interpnumber,
                       cmap=cmap_standard, vmin=limits_z[0], vmax=limits_z[1])
        #ax.scatter(self.data['x'], self.data['y']) #sample poitns positions

        # add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax = addLimitsXY(ax, self.range_x, self.range_y)
        # manually add legend
        cbar = plt.colorbar(cax)
        cbar.ax.set_ylabel(self.label_z)
        return ax