#!python3.6.3
import csv
import math
import numpy as np

from scipy.interpolate import interp2d
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mpl_toolkits.mplot3d import Axes3D
from multiprocessing import Process

def getProjection(plotclass):
    if hasattr(plotclass, 'projection'):
        if plotclass.projection == '3d':
            return '3d'
    return None

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

def saveToCSV(plotclass, csvname):
    columnscsv = []
    plotdata = plotclass.data

    #get dictionary keys specific to class
    dictkeys = None
    if isinstance(plotclass, Plot2D):
        dictkeys = ['x', 'y', 'xsd', 'ysd']
    elif isinstance(plotclass, PlotHist):
        dictkeys = ['x']
    elif isinstance(plotclass, PlotBar):
        dictkeys = ['x', 'ysd', 'labels']
    elif isinstance(plotclass, Plot3D):
        dictkeys = ['x', 'y', 'z']
    elif isinstance(plotclass, PlotMap):
        dictkeys = ['x', 'y', 'z']
    else:
        raise Exception('classtype not recognized, could not save to csv')
    #enter data in columns
    for line in plotdata:
        for i in range(len(dictkeys)):
            dictkey = dictkeys[i]
            labelname = line['label'].replace(' ', '_')
            columnscsv.append([dictkey+'_'+labelname]+list(line[dictkey]))

    #save to csv with different column lengths
    destnamecsv = csvname
    with open(destnamecsv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        index_max = max(len(x) for x in columnscsv)
        for i in range(0, index_max):
            writer.writerow([column[i] for column in columnscsv if i<len(column)])

def plotAndSave(plotclasses, imgname=None, csvname=None, grid=None, aspects=None,
                        saveimg=True, savecsv=True, show=True):
    #makes a subprocess of the plot. This is to avoid wait-times between #todo make this more clear
    #different plots
    args_tuple = tuple(reversed(list(locals().values()))) #locals() is in reversed order
    Process(target=plotAndSaveProcess, args=args_tuple).start()

def plotAndSaveProcess(plotclasses, imgname=None, csvname=None, grid=None, aspects=None,
                        saveimg=True, savecsv=True, show=True):
    #plots a a single plotclass in a single figure or a list of plotclasses
    #in a subfigure
    if type(plotclasses) is not list:
         plotclasses = [plotclasses]

    n = len(plotclasses)
    fig = plt.figure(facecolor='white', edgecolor='white')
    fig.canvas.set_window_title('')
    axs = [None]*n
    if grid is None:
        grid = (n, 1)
    gridx, gridy = grid[1], grid[0]
    for i in range(n):
        ax_raw = fig.add_subplot(gridx, gridy, i+1, projection=getProjection(plotclasses[i]))
        plotclasses[i].checkData()
        axs[i] = plotclasses[i].addAxis(ax_raw)

        if plotclasses[i].legend:
            lgd = axs[i].legend(loc=plotclasses[i].legend_loc)

        aspect = 1
        xmin, xmax = axs[i].get_xlim()
        ymin, ymax = axs[i].get_ylim()
        if type(aspects) is list and len(aspects) >= n:
            aspect = aspects[i]
        axs[i].set_aspect(abs((xmax - xmin) / (ymax - ymin)) * aspect, adjustable='box-forced')
        if savecsv:
            saveToCSV(plotclasses[i], csvname)
    fig.tight_layout()
    if saveimg:
        if type(imgname) is not str:
            raise Exception('destination string is invalid')
        fig.savefig(imgname, bbox_inches='tight')
    if show:
        plt.show()
        plt.close()
    return fig, axs

class PlotParent:
    def __init__(self, data, interpnumber = 10, label_x='x', label_y='y', label_z='z', legend=True,
                 legend_loc='upper right', logx=False, logy=False, projection=None, range_x=None,
                 range_y=None, range_z=None, titlename='', xformat='normal'):
        self.data = data
        self.interpnumber = interpnumber
        self.label_x = label_x
        self.label_y = label_y
        self.label_z = label_z
        self.legend = legend
        self.legend_loc = legend_loc
        self.logx = logx
        self.logy = logy
        self.projection = projection
        self.range_x = range_x
        self.range_y = range_y
        self.range_z = range_z
        self.titlename = titlename
        self.xformat = xformat

    def checkData(self):
        if type(self.data) is dict:
            self.data = [self.data]
        elif not type(list):
            raise Exception("data is not (list of) dictionary(s)")

    def showAndSave(self, imgname=None, csvname=None, saveimg=True, savecsv=True, show=True):
        plotAndSave(self, imgname, csvname, grid=(1,1), aspects=[1], saveimg=saveimg,
                    savecsv=savecsv,
                    show=show)
        return self

class Plot2D(PlotParent):
    def __init__(self, **args):
        super().__init__(**args)

    def addAxis(self, ax):
        #essential keys of dict: 'x', 'y'
        #optional keys of dict: 'label', 'linestyle', 'xsd', 'ysd'
        for d in self.data:
            if 'label' not in d: d['label'] = 'no_label'
            if 'linestyle' not in d: d['linestyle'] = '-'
            if 'show' not in d: d['show'] = True

            if not any(k in d for k in ('xsd', 'ysd')):
                #normal plot
                if d['show'] == True:
                    ax.plot(d['x'], d['y'], d['linestyle'], label=d['label'])
                d['xsd'] = [0] * len(d['x'])
                d['ysd'] = [0] * len(d['y'])
            else:
                #plot with errorbars
                if 'xsd' not in d:
                    d['xsd'] = [0]*len(d['x'])
                elif isinstance(d['xsd'], int) or isinstance(d['xsd'], float):
                    d['xsd'] = [d['xsd']]*len(d['x'])
                if 'ysd' not in d:
                    d['ysd'] = [0]*len(d['y'])
                elif isinstance(d['ysd'], int) or isinstance(d['ysd'], float):
                    d['ysd'] = [d['ysd']]*len(d['y'])
                if d['show'] == True:
                    ax.errorbar(d['x'], d['y'], fmt=d['linestyle'],
                                xerr=d['xsd'], yerr=d['ysd'], label=d['label'],
                                capsize=3)

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

class PlotHist(PlotParent):
    def __init__(self, **args):
        super().__init__(**args)

    def addAxis(self, ax):
        for d in self.data:
            if 'normed' not in d: d['normed'] = None
            if 'alpha' not in d: d['alpha'] = 1
            if 'label' not in d: d['label'] = 'no_label'
            ax.hist(d['x'], d['bins'], normed=d['normed'], alpha=d['alpha'], label=d['label'])
        #add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax = addLimitsXY(ax, self.range_x, self.range_y)
        ax.grid()
        return ax

class PlotBar(PlotParent):
    def __init__(self, **args):
        super().__init__(**args)

    def addAxis(self, ax):
        gap=0.2
        barwidth = (1-gap)/len(self.data) #barwidth=1 is touching bars
        pos = 0
        ind = np.arange(len(self.data[0]['labels']))
        for d in self.data:
            if 'ysd' not in d: d['ysd'] = [0]*len(d['x'])
            if 'label' not in d: d['label'] = 'no_label'
            ax.bar(pos+ind, d['x'], barwidth, label=d['label'], yerr=d['ysd'], capsize=3)
            pos += barwidth
        ax.set_xticks( 1/2*(2*ind-barwidth +1-gap))
        ax.set_xticklabels(self.data[0]['labels'])
        #add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax = addLimitsXY(ax, None, self.range_y)
        ax.grid()
        return ax

class Plot3D(PlotParent):
    def __init__(self, **args):
        super().__init__(**args)
        self.projection = '3d'

    def addAxis(self, ax):
        cmap_standard = plt.cm.get_cmap('RdYlBu')  # define cmap standard
        for d in self.data:
            if 'label' not in d: d['label'] = 'no_label'
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

class PlotMap(PlotParent):
    def __init__(self, **args):
        super().__init__(**args)

    def addAxis(self, ax):
        cmap_standard = plt.cm.get_cmap('RdYlBu')  # define cmap standard
        d = self.data[0]
        if 'label' not in d: self.data[0]['label'] = 'no_label'
        limits_z = [min(d['z']), max(d['z'])]
        if self.range_z is not None:
            limits_z = self.range_z
        cax = ax.tricontourf(d['x'], d['y'], d['z'], self.interpnumber,
                       cmap=cmap_standard, vmin=limits_z[0], vmax=limits_z[1])
        #ax.scatter(self.data['x'], self.data['y']) #sample points positions

        # add
        ax = addLabels(ax, self.titlename, self.label_x, self.label_y)
        ax = addLimitsXY(ax, self.range_x, self.range_y)
        # manually add legend
        cbar = plt.colorbar(cax)
        cbar.ax.set_ylabel(self.label_z)
        return ax