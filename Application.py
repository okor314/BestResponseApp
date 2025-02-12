import sys

import matplotlib.pyplot
from BestResponse import *

import sys
import matplotlib
matplotlib.use('QtAgg')

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, QMenu,
                             QLabel, QLineEdit, QFileDialog, QMessageBox, QFrame,
                             QCheckBox, QPushButton, QRadioButton, QProgressBar,
                             QSlider, QFormLayout, QButtonGroup
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QIntValidator, QPixmap, QImage, QAction, QKeySequence, QDesktopServices, QShortcut

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

def get_script_path():
    if getattr(sys, 'frozen', False):
        # Run with .exe (PyInstaller)
        return os.path.dirname(sys.executable).replace('\\', '/')
    else:
        # Run with .py
        return os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
    
def makeFileName(path, fileName='Response.dat', n=0):
    if n > 100:  # Prevent infinite recursion
        raise Exception("Too many directories with similar names.")
    if  fileName in os.listdir(path):
        fileName = makeFileName(path, f'Response ({n+1}).dat', n+1)
        
    return fileName

def makeCrosses(points):
    rows = sum([(y-1, y, y, y, y+1) for (x,y) in points], ())
    columbs = sum([(x, x-1, x, x+1, x) for (x,y) in points], ())

    return rows, columbs



def mathTex_to_QPixmap(mathTex, fs=10):
    #took it from StackOverflow

    #---- set up a mpl figure instance ----

    fig = matplotlib.figure.Figure()
    fig.patch.set_facecolor('none')
    fig.set_canvas(FigureCanvasQTAgg(fig))
    renderer = fig.canvas.get_renderer()

    #---- plot the mathTex expression ----

    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.patch.set_facecolor('none')
    t = ax.text(0, 0, mathTex, ha='left', va='bottom', fontsize=fs)

    #---- fit figure size to text artist ----

    fwidth, fheight = fig.get_size_inches()
    fig_bbox = fig.get_window_extent(renderer)

    text_bbox = t.get_window_extent(renderer)

    tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
    tight_fheight = text_bbox.height * fheight / fig_bbox.height

    fig.set_size_inches(tight_fwidth, tight_fheight)

    #---- convert mpl figure to QPixmap ----

    buf, size = fig.canvas.print_to_buffer()
    qimage = QImage.rgbSwapped(QImage(buf, size[0], size[1],
                                                  QImage.Format.Format_ARGB32))
    qpixmap = QPixmap(qimage)

    return qpixmap

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self):
        fig = Figure()
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setMouseTracking(True)


class QHLine(QFrame):
    def __init__(self, linewidth=0):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(linewidth)

# Setting parameters window
class ParametersWindow(QMainWindow):
    closeSignal = pyqtSignal()
    parameters = {'indentationX':50, 'indentationY':50, 'preStep':16}
    
    def __init__(self, imagesShape, *args, **kwargs):
        super().__init__(*args, **kwargs)


        self.preSearchDefaultValues = {'indentationX':50, 'indentationY':50, 'preStep':16}
        self.defaultMainValues = {'averagedImagesMode':False, 'step':4, 'radius':16, 'baseline':10, 'npts':3, 'formulaKey':0}

        self.setWindowTitle('Parameters setting')
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Selection Averaged images mode
        self.AvrModeCheckBox = QCheckBox()
        self.AvrModeCheckBox.setCheckState([Qt.CheckState.Unchecked, Qt.CheckState.Checked][BestResponse.averagedImagesMode])
        self.AvrModeCheckBox.setText('Averaged images mode')
        self.AvrModeCheckBox.stateChanged.connect(self.changeAveragedImagesMode)

        # Selection indentation for pre-search
        self.setIndentationX = QLineEdit(str(self.parameters['indentationX']))
        self.setIndentationX.setPlaceholderText(f'0 to {imagesShape[1]//2-1}')
        self.setIndentationX.setValidator(QIntValidator(0, imagesShape[1]//2-1, self))
        self.setIndentationX.editingFinished.connect(self.changeIndentationX)
        self.setIndentationY = QLineEdit(str(self.parameters['indentationY']))
        self.setIndentationY.setPlaceholderText(f'0 to {imagesShape[0]//2-1}')
        self.setIndentationY.setValidator(QIntValidator(0, imagesShape[0]//2-1, self))
        self.setIndentationY.editingFinished.connect(self.changeIndentationY)

        # Selection step for pre-search
        self.setPreStep = QLineEdit(str(self.parameters['preStep']))
        self.setPreStep.setValidator(QIntValidator(1, min(imagesShape), self))
        self.setPreStep.editingFinished.connect(self.changePreStep)

        # Selection main parameters
        self.setStep = QLineEdit(str(BestResponse.step))
        self.setStep.setValidator(QIntValidator(1, min(imagesShape), self))
        self.setStep.editingFinished.connect(self.changeStep)

        self.setRadius = QLineEdit(str(BestResponse.radius))
        self.setRadius.setValidator(QIntValidator(0, min(imagesShape)//2-1, self))
        self.setRadius.editingFinished.connect(self.changeRadius)

        self.setBaseline = QLineEdit(str(BestResponse.baseline))
        self.setBaseline.setValidator(QIntValidator(self, bottom=1))
        self.setBaseline.editingFinished.connect(self.changeBaseline)

        self.setSmoothOrder = QLineEdit(str(BestResponse.npts))
        self.setSmoothOrder.setValidator(QIntValidator(self, bottom=1))
        self.setSmoothOrder.editingFinished.connect(self.changeSmoothOrder)

        # Selection response formula
        formula0 = QLabel()
        formula0.setPixmap(mathTex_to_QPixmap(r'$S = \sqrt{\left(\frac{R}{L} - \frac{R_0}{L_0}\right)^2 + \left(\frac{G}{L} - \frac{G_0}{L_0}\right)^2 + \left(\frac{B}{L} - \frac{B_0}{L_0}\right)^2}$'))
        formula1 = QLabel()
        formula1.setPixmap(mathTex_to_QPixmap(r'$S = \left|\frac{R}{L} - \frac{R_0}{L_0}\right| + \left|\frac{G}{L} - \frac{G_0}{L_0}\right| + \left|\frac{B}{L} - \frac{B_0}{L_0}\right|$'))

        self.setFormula0 = QRadioButton()
        self.setFormula0.toggled.connect(self.changeFormulaKey)
        self.setFormula1 = QRadioButton()
        self.setFormula1.toggled.connect(self.changeFormulaKey)
        [self.setFormula0, self.setFormula1][BestResponse.formulaKey].setChecked(True)

        # Close and Reset buttons
        closeButton = QPushButton("Close")
        closeButton.clicked.connect(self.closeWindow)

        resetParametersButton = QPushButton('Reset default parameters')
        resetParametersButton.clicked.connect(self.resetParameters)
        
        ###############################
        layout = QGridLayout(central_widget)
        layout.addWidget(self.AvrModeCheckBox, 0, 0, 1, 5, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QHLine(linewidth=2), 1, 0, 1, 5)
        layout.addWidget(QLabel('Pre-search parameters'), 2, 0, 1, 5, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QHLine(), 3, 0, 1, 5)
        layout.addWidget(QLabel('Indentation from the edges:'), 4, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(QLabel('n_x ='), 4, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setIndentationX, 4, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel('n_y ='), 4, 3, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setIndentationY, 4, 4, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel('Pre-Step:'), 5, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setPreStep, 5, 1, 1, 4, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(QHLine(linewidth=2), 6, 0, 1, 5)
        layout.addWidget(QLabel('Main parameters'), 7, 0, 1, 5, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QHLine(), 8, 0, 1, 5)
        layout.addWidget(QLabel('Step:'), 9, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setStep, 9, 1, 1, 4, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel('Radius of RGB averaging:'), 10, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setRadius, 10, 1, 1, 4, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel('Baseline points number:'), 11, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setBaseline, 11, 1, 1, 4, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel('Order of smoothing:'), 12, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setSmoothOrder, 12, 1, 1, 4, alignment=Qt.AlignmentFlag.AlignLeft)

        
        layout.addWidget(QLabel('Response formula:'), 13, 0, 2, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setFormula0, 13, 1)
        layout.addWidget(self.setFormula1, 14, 1)
        layout.addWidget(formula0, 13, 2, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(formula1, 14, 2, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(QHLine(linewidth=2), 15, 0, 1, 5)
        
        layout.addWidget(closeButton, 16, 4)
        layout.addWidget(resetParametersButton, 16, 2, 1, 2)

        
        
        self.show()

    def closeWindow(self):
        self.closeSignal.emit()
        self.close()

    def resetParameters(self):
        self.parameters.update(self.preSearchDefaultValues)
        for key, item in self.defaultMainValues.items():
            setattr(BestResponse, key, item)
        self.closeSignal.emit()
        self.close()

    def changeAveragedImagesMode(self):
        BestResponse.averagedImagesMode = self.AvrModeCheckBox.isChecked()
    
    def changeIndentationX(self):
        text = self.setIndentationX.text()
        self.parameters['indentationX'] = int(text)


    def changeIndentationY(self):
        text = self.setIndentationY.text()
        self.parameters['indentationY'] = int(text)


    def changePreStep(self):
        text = self.setPreStep.text()
        self.parameters['preStep'] = int(text)

    def changeStep(self):
        text = self.setStep.text()
        BestResponse.step = int(text)

    def changeRadius(self):
        text = self.setRadius.text()
        BestResponse.radius = int(text)

    def changeBaseline(self):
        text = self.setBaseline.text()
        BestResponse.baseline = int(text)

    def changeSmoothOrder(self):
        text = self.setSmoothOrder.text()
        BestResponse.npts = int(text)

    def changeFormulaKey(self):
        if self.setFormula0.isChecked():
            BestResponse.formulaKey = 0
        elif self.setFormula1.isChecked():
            BestResponse.formulaKey = 1

    def changeWeightFunc(self):
        if self.avrWButton.isChecked():
            BestResponse.weightFunc = lambda _, x: np.mean(np.sort(x)[-3:])
        elif self.sumWButton.isChecked():
            BestResponse.weightFunc = sum
            
#################################################

class PreSearchWindow(QMainWindow):
    okSignal = pyqtSignal()
    
    def __init__(self, imagesShape, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Pre-seacrh setting')

        self.advancedWindow = None
        self.imagesShape = imagesShape
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Selection Averaged images mode
        self.AvrModeCheckBox = QCheckBox()
        self.AvrModeCheckBox.setCheckState([Qt.CheckState.Unchecked, Qt.CheckState.Checked][BestResponse.averagedImagesMode])
        self.AvrModeCheckBox.setText('Averaged images mode')
        self.AvrModeCheckBox.stateChanged.connect(lambda: setattr(BestResponse, 'averagedImagesMode', self.AvrModeCheckBox.isChecked()))

        # Selection indentation for pre-search
        self.setIndentationX = QLineEdit(str(ParametersWindow.parameters['indentationX']))
        self.setIndentationX.setPlaceholderText(f'0 to {imagesShape[1]//2-1}')
        self.setIndentationX.setValidator(QIntValidator(0, imagesShape[1]//2-1, self))
        self.setIndentationX.editingFinished.connect(lambda: ParametersWindow.parameters.update({'indentationX':int(self.setIndentationX.text())}))
        self.setIndentationY = QLineEdit(str(ParametersWindow.parameters['indentationY']))
        self.setIndentationY.setPlaceholderText(f'0 to {imagesShape[0]//2-1}')
        self.setIndentationY.setValidator(QIntValidator(0, imagesShape[0]//2-1, self))
        self.setIndentationY.editingFinished.connect(lambda: ParametersWindow.parameters.update({'indentationY':int(self.setIndentationY.text())}))

        # Selection step for pre-search
        self.setPreStep = QLineEdit(str(ParametersWindow.parameters['preStep']))
        self.setPreStep.setValidator(QIntValidator(1, min(imagesShape), self))
        self.setPreStep.editingFinished.connect(lambda: ParametersWindow.parameters.update({'preStep':int(self.setPreStep.text())}))

        self.okButton = QPushButton("Ok")
        self.okButton.clicked.connect(self.ok)

        self.advanceButton = QPushButton("Advanced settings")
        self.advanceButton.clicked.connect(self.advancedSettings)

        ####
        layout = QGridLayout(central_widget)
        
        layout.addWidget(QHLine(linewidth=2), 0, 0, 1, 5)
        layout.addWidget(QLabel('Pre-search parameters'), 1, 0, 1, 5, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QHLine(), 2, 0, 1, 5)
        layout.addWidget(QLabel('Indentation from the edges:'), 3, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(QLabel('n_x ='), 3, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setIndentationX, 3, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel('n_y ='), 3, 3, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setIndentationY, 3, 4, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(QLabel('Pre-Step:'), 4, 0, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.setPreStep, 4, 1, 1, 4, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.AvrModeCheckBox, 5, 0, 1, 5, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.okButton, 6, 4)
        layout.addWidget(self.advanceButton, 6, 2, 1, 2)
        


        self.show()

    def ok(self):
        ParametersWindow.parameters.update({'indentationX':int(self.setIndentationX.text()),
                                            'indentationY':int(self.setIndentationY.text()),
                                            'preStep':int(self.setPreStep.text())})
        BestResponse.averagedImagesMode = self.AvrModeCheckBox.isChecked()
        self.okSignal.emit()
        self.close()

    def updateLines(self):
        self.setIndentationX.clear()
        self.setIndentationX.insert(str(ParametersWindow.parameters['indentationX']))

        self.setIndentationY.clear()
        self.setIndentationY.insert(str(ParametersWindow.parameters['indentationY']))

        self.setPreStep.clear()
        self.setPreStep.insert(str(ParametersWindow.parameters['preStep']))

        self.AvrModeCheckBox.setCheckState([Qt.CheckState.Unchecked, Qt.CheckState.Checked][BestResponse.averagedImagesMode])

        self.advancedWindow = None

    def advancedSettings(self):
        if self.advancedWindow == None:
            self.advancedWindow = ParametersWindow(self.imagesShape)
            self.advancedWindow.closeSignal.connect(self.updateLines)
        
            
class ExplainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('Parameters explanation')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QFormLayout(central_widget)

        text = 'In the selected region, the program takes an array of points (nodes). For each point, the response (versus time) and the weighting factor are calculated. Of all the points, the one with the highest weighting factor is returned. The weighting factor is calculated as the average of the three largest values of the smoothed response.\nAll main parameters except Step are also used in pre-search'     
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(label)

        layout.addRow(QHLine(linewidth=2))
        text = 'If you check the box, images averaged along the Y-axis will be used in the calculations.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Averaged\nimages mode:'), label)

        layout.addRow(QHLine(linewidth=2))
        layout.addRow(QLabel('Pre-search parameters'))
        layout.addRow(QHLine(linewidth=2))

        text = 'The indentations n_x and n_y is the distance from the edges of the image along the x and y axes, respectively. They form the pre-search region. By default, n_x and n_y are 50 pixels.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Indentations:'), label)
        layout.addRow(QHLine(linewidth=0))

        text = 'Distance between neighboring points (nodes) for the pre-search region. The default is 16 pixels.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Pre-Step:'), label)

        layout.addRow(QHLine(linewidth=2))
        layout.addRow(QLabel('Main parameters'))
        layout.addRow(QHLine(linewidth=2))

        text = 'Distance between neighboring points (nodes) for the selected region. The default is 4 pixels.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Step:'), label)
        layout.addRow(QHLine(linewidth=0))

        text = 'The response is calculated using the averaged values of the R, G, B components around the point. The averaging area is a square centered at this point and with a side of 2r + 1 pixels, where r is the radius. The default radius is 16 pixels.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Radius of\nRGB averaging:'), label)
        layout.addRow(QHLine(linewidth=0))

        text = 'Number of images of the initial state of the system. The default is 10.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Baseline\npoints number:'), label)
        layout.addRow(QHLine(linewidth=0))

        text = 'Smoothing is performed using an FFT low-pass parabolic filter with a cutoff frequency of f = 1/(2*order*delta_t). The weighting coefficients of the inverse Fourier transform for high-frequency components are given by a parabola with a maximum of 1 at the zero frequency and decreasing to zero at the cutoff frequency. The default value is 3.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Order\nof smoothing:'), label)
        layout.addRow(QHLine(linewidth=0))

        text = 'The formula for calculating the response at a given time.'
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addRow(QLabel('Response\nformula:'), label)



        self.show()
#################################################
            
class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.preferredPath = get_script_path()
        self.fileNames = None
        self.images = None
        self.regions = dict()
        self.preSearchRegion = None
        self.preSearchResponse = None
        self.shownPicture = None
        self.shownPoints = None
        self.pressFlag = False

        self.explainWindow = None
        self.parametersWindow = None

        self.progressbar = QProgressBar()

        self.setWindowTitle('BestResponse')

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QGridLayout(self.central_widget)

        self.startText = QLabel('To get started, create a new project')
        self.startText.setStyleSheet("""color : grey;
                                font-size: 24px""")
        self.layout.addWidget(self.startText, 0, 0, 4, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        
        
        
        #####
        newProjectAction = QAction('&New Project', self)
        newProjectAction.triggered.connect(self.openFileDialog)
        newProjectAction.setShortcut(QKeySequence("Ctrl+n"))
        newProjectAction.setStatusTip("Create a new project")

        saveAction = QAction("*.dat RGB + S", self)
        saveAction.triggered.connect(lambda: self.saveData(key='RGB+S'))
        saveAction.setShortcut(QKeySequence("Ctrl+s"))
        saveAction.setStatusTip("Save RGB and Response data in *.dat file")

        saveOnlyRGBAction = QAction("*.dat RGB", self)
        saveOnlyRGBAction.triggered.connect(lambda: self.saveData(key='RGB'))
        saveOnlyRGBAction.setStatusTip("Save only RGB data in *.dat file")

        saveOnlySAction = QAction("*.dat S", self)
        saveOnlySAction.triggered.connect(lambda: self.saveData(key='S'))
        saveOnlySAction.setStatusTip("Save only Response data in *.dat file")

        exitAction = QAction("Exit", self)
        exitAction.triggered.connect(self.close)
        exitAction.setShortcut(QKeySequence("Ctrl+q"))

        changeParametersAction = QAction("Change", self)
        changeParametersAction.triggered.connect(self.changeParameters)
        changeParametersAction.setShortcut(QKeySequence("Ctrl+p"))
        changeParametersAction.setStatusTip("Change the values of parameters")

        explanationAction = QAction('About...', self)
        explanationAction.triggered.connect(self.parametersExplanation)
        explanationAction.setStatusTip("View explanations of the parameters")

        instructionAction = QAction('Instruction', self)
        instructionAction.triggered.connect(lambda: self.openLink('https://github.com/okor314/BestResponseApp/blob/main/README.md'))
        instructionAction.setStatusTip("Open instruction to the program in browser")
        programCode = QAction('Program Code', self)
        programCode.triggered.connect(lambda: self.openLink('https://github.com/okor314/BestResponseApp'))

        compare = QShortcut(QKeySequence("Ctrl+Return"), self)
        compare.activated.connect(self.compareWeigthFuncs)
        

        #####
        self.statusbar = self.statusBar()
        menubar = self.menuBar()

        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(newProjectAction)

        saveMenu = fileMenu.addMenu("Save as")
        saveMenu.addAction(saveAction)
        saveMenu.addAction(saveOnlyRGBAction)
        saveMenu.addAction(saveOnlySAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)

        parametersMenu = menubar.addMenu("&Parameters")
        parametersMenu.addAction(changeParametersAction)
        parametersMenu.addAction(explanationAction)

        helpMenu = menubar.addMenu("&Help")
        helpMenu.addAction(instructionAction)
        helpMenu.addAction(programCode)


        self.showMaximized()
        self.show()


    def updateShownPicture(self):
        if self.images.averagedImagesMode != BestResponse.averagedImagesMode:
            self.images = Images(self.fileNames, BestResponse.averagedImagesMode)

        self.shownPicture = self.images[0].copy()
        self.shownPicture[self.preSearchRegion.getBoundaries()] = [255, 255, 255]

        self.shownPicture[self.shownPoints[0][:5*self.slider.value()],
                          self.shownPoints[1][:5*self.slider.value()]] = [255, 255, 255]
        
        for region in self.regions:
            self.shownPicture[region.getBoundaries()] = [0, 0, 0]

        # self.picture.axes.clear()
        # self.picture.axes.imshow(self.shownPicture)
        # self.picture.draw()

        self.pictureAxes.set_data(self.shownPicture)
        self.picture.draw()

        self.sliderText.setText(f"Shown points: {self.slider.value()}")

    def doPreSearch(self):
        if self.images.averagedImagesMode != BestResponse.averagedImagesMode:
            self.images = Images(self.fileNames, BestResponse.averagedImagesMode)

        x1, y1 = ParametersWindow.parameters['indentationX'], ParametersWindow.parameters['indentationY']
        x2, y2 = self.images.shape[1]-1-ParametersWindow.parameters['indentationX'], self.images.shape[0]-1-ParametersWindow.parameters['indentationY']
        self.preSearchRegion = Rectangle((x1,y1), (x2,y2))

        self.preSearchResponse = BestResponse(self.images, self.preSearchRegion)
        self.preSearchResponse.step = ParametersWindow.parameters['preStep']

        self.progressbar.show()
        self.preSearchResponse.sortPoints(progressBar=self.progressbar)
        self.progressbar.hide()

        self.shownPoints = makeCrosses([item[0] for item in self.preSearchResponse.sortedPoints])
        
        self.slider.setRange(0, len(self.preSearchResponse.sortedPoints))
        self.slider.setValue(round(0.1*self.slider.maximum()))
        self.slider.setTickInterval(round(0.1*self.slider.maximum()))
        self.slider.setTickPosition(QSlider.TickPosition.TicksLeft)

        self.updateShownPicture()

        
    def scanning(self):
        if self.images.averagedImagesMode != BestResponse.averagedImagesMode:
            self.images = Images(self.fileNames, BestResponse.averagedImagesMode)
            for region in self.regions:
                self.regions[region] = BestResponse(self.images, region)

        numRegions = len(self.regions)
        if numRegions == 0: return

        self.progressbar.show()
        for region in self.regions:
            self.regions[region].sortPoints(progressBar=self.progressbar)
        self.progressbar.hide()

        if numRegions == 1:
            matplotlib.pyplot.figure()
            response = self.regions[list(self.regions)[0]]
            R, G, B, S, smooth_S, _, _ = response.getDataInPoint(response.bestPoint)
            t = range(1, len(R)+1)

            L = np.sqrt(R**2 + G**2 + B**2)
            Rcos = R/L
            Gcos = G/L
            Bcos = B/L

            matplotlib.pyplot.subplot(2, 1, 1)
            matplotlib.pyplot.plot(t, S, linestyle='-', linewidth=1, marker='s', markersize=5, color='k', label='Response')
            matplotlib.pyplot.plot(range(1, len(smooth_S)+1), smooth_S, linestyle='-', linewidth=1, marker='o', markersize=5, color='r', label='Smooth')
            matplotlib.pyplot.title(f'Region №{1}$, x={response.bestPoint[0]}$, $y={response.bestPoint[1]}$')
            matplotlib.pyplot.xlabel('Time, rel. un.')
            matplotlib.pyplot.ylabel('Response')
            matplotlib.pyplot.legend()

            matplotlib.pyplot.subplot(2, 1, 2)
            matplotlib.pyplot.plot(t, Rcos,  linestyle='-', linewidth=1, marker='s', markersize=5, color='r', label='R/L')
            matplotlib.pyplot.plot(t, Gcos,  linestyle='-', linewidth=1, marker='o', markersize=5, color='g', label='G/L')
            matplotlib.pyplot.plot(t, Bcos,  linestyle='-', linewidth=1, marker='^', markersize=5, color='b', label='B/L')
            matplotlib.pyplot.xlabel('Time, rel. un.')
            matplotlib.pyplot.legend()

            matplotlib.pyplot.tight_layout()
            matplotlib.pyplot.show()
        else:
            matplotlib.pyplot.figure()
            i = 1
            for _, response in self.regions.items():
                R, G, B, S, smooth_S, _, _ = response.getDataInPoint(response.bestPoint)
                t = range(1, len(R)+1)

                L = np.sqrt(R**2 + G**2 + B**2)
                Rcos = R/L
                Gcos = G/L
                Bcos = B/L

                matplotlib.pyplot.subplot(2, numRegions+1, i)
                matplotlib.pyplot.plot(t, S, linestyle='-', linewidth=1, marker='s', markersize=5, color='k', label='Response')
                matplotlib.pyplot.plot(range(1, len(smooth_S)+1), smooth_S, linestyle='-', linewidth=1, marker='o', markersize=5, color='r', label='Smooth')
                matplotlib.pyplot.title(f'Region №{i}$, x={response.bestPoint[0]}$, $y={response.bestPoint[1]}$')
                matplotlib.pyplot.xlabel('Time, rel. un.')
                matplotlib.pyplot.ylabel('Response')
                matplotlib.pyplot.legend()

                matplotlib.pyplot.subplot(2, numRegions+1, numRegions+1+i)
                matplotlib.pyplot.plot(t, Rcos,  linestyle='-', linewidth=1, marker='s', markersize=5, color='r', label='R/L')
                matplotlib.pyplot.plot(t, Gcos,  linestyle='-', linewidth=1, marker='o', markersize=5, color='g', label='G/L')
                matplotlib.pyplot.plot(t, Bcos,  linestyle='-', linewidth=1, marker='^', markersize=5, color='b', label='B/L')
                matplotlib.pyplot.xlabel('Time, rel. un.')
                matplotlib.pyplot.legend()

                i += 1
            
            multyResponse = combineResponses([response for _, response in self.regions.items()], formulaKey=BestResponse.formulaKey)
            smoothMultyResponse = BestResponse.smoothFFT(self, multyResponse, order=BestResponse.npts)
            matplotlib.pyplot.subplot(2, numRegions+1, i)
            matplotlib.pyplot.plot(t, multyResponse, linestyle='-', linewidth=1, marker='s', markersize=5, color='k', label='Response')
            matplotlib.pyplot.plot(range(1, len(smoothMultyResponse)+1), smoothMultyResponse,
                                    linestyle='-', linewidth=1, marker='o', markersize=5, color='r', label='Smooth')
            matplotlib.pyplot.title(f'Combine Responses')
            matplotlib.pyplot.xlabel('Time, rel. un.')
            matplotlib.pyplot.ylabel('Response')
            matplotlib.pyplot.legend()

            matplotlib.pyplot.tight_layout()
            matplotlib.pyplot.show()

    def compareWeigthFuncs(self):
        i=0
        for region in self.regions:
            i += 1
            resp = BestResponse(self.images, region)
            fig, ax = matplotlib.pyplot.subplots(1, 3)
            fig.suptitle(f'Region №{i}')

            self.progressbar.show()
            resp.sortPoints(weightFunc=lambda x: np.mean(np.sort(x)[-3:]) , progressBar=self.progressbar)
            self.progressbar.hide()
            R, G, B, S, smooth_S1, _, _ = resp.getDataInPoint(resp.bestPoint)
            t = range(1, len(S)+1)
            ax[0].plot(t, S, linestyle='-', linewidth=1, marker='s', markersize=5, color='k', label='Response')
            ax[0].plot(range(1, len(smooth_S1)+1), smooth_S1, linestyle='-', linewidth=1, marker='o', markersize=5, color='r', label='Smooth')
            ax[0].set_title(f'By max response, $x={resp.bestPoint[0]}$, $y={resp.bestPoint[1]}$')
            ax[0].set(xlabel='Time, rel. un.', ylabel='Response')
            ax[0].legend()

            self.progressbar.show()
            resp.sortPoints(weightFunc=sum, progressBar=self.progressbar)
            self.progressbar.hide()
            R, G, B, S, smooth_S2, _, _ = resp.getDataInPoint(resp.bestPoint)
            t = range(1, len(S)+1)
            ax[1].plot(t, S, linestyle='-', linewidth=1, marker='s', markersize=5, color='k', label='Response')
            ax[1].plot(range(1, len(smooth_S2)+1), smooth_S2, linestyle='-', linewidth=1, marker='o', markersize=5, color='b', label='Smooth')
            ax[1].set_title(f'By sum, $x={resp.bestPoint[0]}$, $y={resp.bestPoint[1]}$')
            ax[1].set(xlabel='Time, rel. un.', ylabel='Response')
            ax[1].legend()

            ax[2].plot(range(1, len(smooth_S1)+1), smooth_S1, linestyle='-', linewidth=1, marker='o', markersize=5, color='r', label='by max')
            ax[2].plot(range(1, len(smooth_S2)+1), smooth_S2, linestyle='-', linewidth=1, marker='o', markersize=5, color='b', label='by sum')
            ax[2].set_title(f'Comparison of smoothed responses')
            ax[2].set(xlabel='Time, rel. un.', ylabel='Response')
            ax[2].legend()

            fig.tight_layout()
            fig.show()

    def createHomePage(self):
        if self.shownPicture is None:
            self.layout.removeWidget(self.startText)
            self.startText.deleteLater()

            self.repeatButton = QPushButton("Repeat pre-Search")
            self.repeatButton.clicked.connect(self.doPreSearch)
            #self.repeatButton.setFixedSize(QSize(200, 50))
            self.layout.addWidget(self.repeatButton, 0, 0)

            self.deleteRegionButton = QPushButton("Delete region")
            self.deleteRegionButton.clicked.connect(self.delLastRegion)
            self.deleteRegionButton.setShortcut("Ctrl+z")
            self.deleteRegionButton.setStatusTip('Delete the last selected region')
            #self.deleteRegionButton.setFixedSize(QSize(200, 50))
            self.layout.addWidget(self.deleteRegionButton, 0, 1)

            self.scanningButton = QPushButton("Start scanning")
            self.scanningButton.clicked.connect(self.scanning)
            self.scanningButton.setShortcut("Return")
            self.scanningButton.setStatusTip('Find the best response in each region')
            #self.scanningButton.setFixedSize(QSize(200, 50))
            self.layout.addWidget(self.scanningButton, 0, 2)

            self.picture = MplCanvas()
            self.picture.mpl_connect("motion_notify_event", self.mouseMoveEvent)
            self.picture.mpl_connect("button_press_event", self.onPress)
            self.picture.mpl_connect("button_release_event", self.onRelease)
            self.layout.addWidget(self.picture, 1, 0, 1, 3)

            self.slider = QSlider(Qt.Orientation.Vertical, self)
            self.slider.setStatusTip('Move to change number of shown poins')
            self.slider.valueChanged.connect(self.updateShownPicture)
            self.layout.addWidget(self.slider, 1, 3)

            self.sliderText = QLabel()
            self.layout.addWidget(self.sliderText, 0, 3)

            self.statusbar.addPermanentWidget(self.progressbar)
  
        self.images = Images(self.fileNames, BestResponse.averagedImagesMode)
        x1, y1 = ParametersWindow.parameters['indentationX'], ParametersWindow.parameters['indentationY']
        x2, y2 = self.images.shape[1]-1-ParametersWindow.parameters['indentationX'], self.images.shape[0]-1-ParametersWindow.parameters['indentationY']
        self.preSearchRegion = Rectangle((x1,y1), (x2,y2))
        
        self.shownPicture = self.images[0].copy()
        self.shownPicture[self.preSearchRegion.getBoundaries()] = [255, 255, 255]    


        self.picture.axes.clear()
        self.pictureAxes = self.picture.axes.imshow(self.shownPicture)
        self.picture.draw()
        self.picture.axes.set_title('Select the search regions with the cursor')

        self.regions = {}

        if self.images.lenght < BestResponse.baseline:
            BestResponse.baseline = self.images.lenght
            text = f"""The number of images in the selected folder is less than the number of baseline points.
The number of baseline points is set to {BestResponse.baseline}.
If necessary, change this by going to the Parameters"""
            QMessageBox.warning(self, 'Number of baseline points changed', text)

        QTimer.singleShot(0, self.doPreSearch)
                      

        
    
    def openFileDialog(self):
            
        fDialog = QFileDialog(self)
        fDialog.setFileMode(QFileDialog.FileMode.Directory)
        fDialog.setViewMode(QFileDialog.ViewMode.List)
        fDialog.setDirectory(self.preferredPath)
        

        if fDialog.exec():
            preferredPath = fDialog.selectedFiles()[0]
            fileNames = [preferredPath+'/'+file for file in os.listdir(preferredPath) if file.endswith('.jpg')]

            if len(fileNames) > 1:
                self.preferredPath = preferredPath
                self.fileNames = fileNames
                self.preSearchWindow = PreSearchWindow(Images(self.fileNames).shape)
                self.preSearchWindow.okSignal.connect(self.createHomePage)
            elif len(fileNames) == 0:
                QMessageBox.critical(self, 'No images in folder', 'There is no images in selected folder. Select another folder with images or add images to this folder.')
            elif len(fileNames) == 1:
                QMessageBox.critical(self, 'Only one image in folder', 'There should be at least 2 images in folder. Select another folder with images or add images to this folder.')

    def saveData(self, key='RGB+S'):
        if self.regions == {}:
            QMessageBox.warning(self, 'No regions is selected', 'Select some regions and try again.')
            return
        elif all([response.bestPoint is None for _, response in self.regions.items()]):
            QMessageBox.warning(self, 'No regions is scanned', 'Scan regions before saving data.')
            return

        saveMode = {'RGB+S': np.s_[0:0],
                    'RGB': np.s_[4:],
                    'S': np.s_[1:4]}
        
        filePath, _ = QFileDialog.getSaveFileName(
        None,  # Parent widget
        "Save File",  # Dialog title
        self.preferredPath +'/'+ makeFileName(self.preferredPath, fileName='Response.dat', n=0),  # Default file name
        "Text Files (*.dat)"  # File filters
        )
        if filePath == '': return

        headers = np.array(['t', 'R', 'G', 'B', 'S', 'sm_S'])
        textList = []

        for _, response in self.regions.items():
            if response.bestPoint is None: continue
            R, G, B, S, smooth_S, *_ = response.getDataInPoint(response.bestPoint)
            t = range(1, len(R)+1)

            S = np.round(S, 5)
            smooth_S = np.round(smooth_S, 5)
            
            t = list(map(str, t))
            R = list(map(str, R))
            G = list(map(str, G))
            B = list(map(str, B))
            S = list(map(str, S))
            smooth_S = list(map(str, smooth_S))
            if len(S) != len(smooth_S): smooth_S.append('')

            data = np.array([t, R, G, B, S, smooth_S])
            data = np.delete(data, saveMode[key], 0)

            text = '\n'.join(['\t'.join(row) for row in data.T])
            text = '\t'.join(np.delete(headers, saveMode[key])) + '\n' + text
            text = '\t'.join(np.delete([str(response.bestPoint), '', '', '', ''], saveMode[key])) + '\n' + text
            textList.append(text)

        if len(self.regions) > 1 and sum([response.bestPoint is not None for _, response in self.regions.items()]) > 1:
            multyResponse = combineResponses([response for _, response in self.regions.items() if response.bestPoint is not None],
                                            formulaKey=BestResponse.formulaKey)
            smoothMultyResponse = BestResponse.smoothFFT(self, multyResponse, order=BestResponse.npts)

            multyResponse = np.round(multyResponse, 5)
            multyResponse = list(map(str, multyResponse))
            smoothMultyResponse = np.round(smoothMultyResponse, 5)
            smoothMultyResponse = list(map(str, smoothMultyResponse))
            if len(multyResponse) != len(smoothMultyResponse): smoothMultyResponse.append('')
            data = np.array([t, multyResponse, smoothMultyResponse])
            text = 't\tMultyS\tSmooth\n' + '\n'.join(['\t'.join(row) for row in data.T])
            text = 'Combined Response\n' + text
            textList.append(text)

        finalText = '\n'.join(['\t'.join(row) for row in np.array([tex.split('\n') for tex in textList]).T])
        

        file = open(filePath, 'w')
        file.write(finalText)
        file.close()
            


    def mouseMoveEvent(self, event):
        if self.picture.underMouse():
            if event.inaxes == self.picture.axes:
                x, y = int(event.xdata), int(event.ydata)
                self.statusbar.showMessage(f"x={x}, y={y}    [R,G,B]={np.array2string(self.images[0][y,x], separator=', ')}")

                if self.pressFlag:
                    upPoint = (min(x, self.firstPoint[0]), min(y, self.firstPoint[1]))
                    dowmPoint = (max(x, self.firstPoint[0]), max(y, self.firstPoint[1]))
                    if upPoint == dowmPoint: print()

                    temporaryPicture = self.shownPicture.copy()
                    try:
                        temporaryPicture[Rectangle(upPoint, dowmPoint).getBoundaries()] = [0, 0, 0]
                    except:
                        print(Rectangle(upPoint, dowmPoint).getBoundaries(), upPoint, dowmPoint)

                    # self.picture.axes.clear()
                    # self.picture.axes.imshow(temporaryPicture)
                    # self.picture.draw()

                    self.pictureAxes.set_data(temporaryPicture)
                    self.picture.draw()
            else:
                self.statusbar.clearMessage()

            

    def onPress(self, event):
        if event.inaxes == self.picture.axes:
            self.firstPoint = (int(event.xdata), int(event.ydata))
            self.pressFlag = True

    def onRelease(self, event):
        self.pressFlag = False

        if event.inaxes == self.picture.axes:
            x, y = int(event.xdata), int(event.ydata)
            upPoint = (min(x, self.firstPoint[0]), min(y, self.firstPoint[1]))
            dowmPoint = (max(x, self.firstPoint[0]), max(y, self.firstPoint[1]))
            if upPoint == dowmPoint: return
            reg = Rectangle(upPoint, dowmPoint)

            self.regions[reg] = BestResponse(self.images, reg)
        
        self.updateShownPicture()
    
    def delLastRegion(self):
        if self.regions:
            self.regions.popitem()
            self.updateShownPicture()

    def changeParameters(self):
        if  self.images is not None:
            if self.parametersWindow is not None and self.parametersWindow.isVisible():
                self.parametersWindow.activateWindow()
            else:
                self.parametersWindow = ParametersWindow(self.images.shape)
        

    def parametersExplanation(self):
        self.explainWindow = ExplainWindow()

    def openLink(self, link):
        # Define the URL to open
        url = QUrl(link)

        # Open the URL in the default web browser
        if not QDesktopServices.openUrl(url):
            self.statusBar().showMessage("Failed to open URL")

    def closeEvent(self, event):
        if self.parametersWindow: self.parametersWindow.close()
        if self.explainWindow: self.explainWindow.close()



app = QApplication(sys.argv)
w = MainWindow()
app.exec()


        
