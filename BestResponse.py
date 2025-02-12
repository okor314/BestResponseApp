import numpy as np
import matplotlib.pyplot as plt

#import time
import os

class Images():
    def  __init__(self, fileNames, averagedImagesMode=False):
        self.fileNames = fileNames
        self.images = self.getImages(mode=averagedImagesMode)
        self.shape = self.images.shape[1:3]
        self.lenght = len(self.images)
        self.averagedImagesMode = averagedImagesMode

    def getMeanRGB(self, x, y, radius=0):
        if y-radius < 0 or x-radius < 0 or y+radius+1>self.shape[0] or x+radius+1>self.shape[1]:
            return None # Change later
        
        return np.mean(self.images[:, y-radius:y+radius+1, x-radius:x+radius+1, :], axis=(1,2)).astype(int)
    

    def getImages(self, mode=False):
        if mode:
            shape_y = plt.imread(self.fileNames[0]).shape[0]
            images = np.array([plt.imread(file) for file in self.fileNames])
            return np.array([np.repeat(np.round(np.mean(image, axis=0)).astype(int)[None,:], shape_y, axis=0) for image in images])
        else:
            return np.array([plt.imread(file) for file in self.fileNames])

    def __getitem__(self, index):
        return self.images[index]

class Rectangle():
    def __init__(self, upPoint, downPoint):
        self.upPointCoord = upPoint
        self.downPointCoord = downPoint

        self.boundaries = self.getBoundaries()

    def createNods(self, step = 1):
        if step < 1:
            return None
        
        return [(x, y) for x in range(self.upPointCoord[0], self.downPointCoord[0]+1, step)
                for y in range(self.upPointCoord[1], self.downPointCoord[1]+1, step)]

    def getBoundaries(self):
        xUpSide = np.array(range(self.upPointCoord[0],self.downPointCoord[0]+1)).astype(int)
        xDownSide = xUpSide
        xLeftSide = np.array([self.upPointCoord[0] for _ in range(self.upPointCoord[1]+1,self.downPointCoord[1])]).astype(int)
        xRightSide = np.array([self.downPointCoord[0] for _ in range(self.upPointCoord[1]+1,self.downPointCoord[1])]).astype(int)

        yUpSide = np.array([self.upPointCoord[1] for _ in range(self.upPointCoord[0],self.downPointCoord[0]+1)]).astype(int)
        yDownSide = np.array([self.downPointCoord[1] for _ in range(self.upPointCoord[0],self.downPointCoord[0]+1)]).astype(int)
        yLeftSide = np.array(range(self.upPointCoord[1]+1,self.downPointCoord[1])).astype(int)
        yRightSide = yLeftSide

        return np.concatenate((yUpSide, yLeftSide, yDownSide, yRightSide), axis=None), np.concatenate((xUpSide, xLeftSide, xDownSide, xRightSide), axis=None)
    

class BestResponse():
    averagedImagesMode = False
    step = 4
    radius = 16
    baseline = 10
    npts = 3
    formulaKey = 0
    weightFunc = lambda _, x: np.mean(np.sort(x)[-3:])

    def __init__(self, images, region):
        self.images = images
        self.region = region
        self.bestPoint = None

        if self.images.lenght <= self.baseline: self.baseline = self.images.lenght


    def smoothFFT(self, data, order=3, dx=1):
        n = len(data)

        freq_cutoff = 1 / (2*order*dx)
        freq = np.fft.rfftfreq(n, dx)

        low_pass_weights = np.zeros_like(freq)
        low_pass_weights[np.abs(freq) <= freq_cutoff] = 1.0
        low_pass_weights = low_pass_weights * np.array([1-(f/freq_cutoff)**2 for f in freq])

        fft_data = np.fft.rfft(data)
        filtered_fft_data = fft_data * low_pass_weights

        return np.fft.irfft(filtered_fft_data)

    
    def sortPoints(self, weightFunc=None , progressBar=None):
        self.sortedPoints = [((-1,-1), -1)]
        if weightFunc is None:
            weightFunc = self.weightFunc

        if progressBar != None:
            progressBar.setValue(0)
            progress = 0

        if self.averagedImagesMode:
            y = (self.region.upPointCoord[1] + self.region.downPointCoord[1]) // 2
            nods_x = range(self.region.upPointCoord[0], self.region.downPointCoord[0]+1, self.step)
            if progressBar != None:
                progressBar.setMaximum(len(nods_x))
            
            for x in nods_x:
                if y-self.radius < 0 or x-self.radius < 0 or y+self.radius+1>self.images.shape[0] or x+self.radius+1>self.images.shape[1]: continue
                R, G, B = self.images.getMeanRGB(x, y, self.radius).T
                
                R0 = np.repeat(np.mean(R[:self.baseline]), repeats=self.images.lenght)
                G0 = np.repeat(np.mean(G[:self.baseline]), repeats=self.images.lenght)
                B0 = np.repeat(np.mean(B[:self.baseline]), repeats=self.images.lenght)

                L = np.sqrt(R**2 + G**2 + B**2)
                L0 = np.sqrt(R0**2 + G0**2 + B0**2)

                if self.formulaKey == 0:
                    S = np.sqrt((R/L - R0/L0)**2 + (G/L - G0/L0)**2 + (B/L - B0/L0)**2)
                elif self.formulaKey == 1:
                    S = np.abs(R/L - R0/L0) + np.abs(G/L - G0/L0) + np.abs(B/L - B0/L0)
                smooth_S = self.smoothFFT(S, order=self.npts)
                weight = weightFunc(smooth_S)

                left = 0
                right = len(self.sortedPoints)
                while left < right:
                    mid = (left + right) // 2
                    if self.sortedPoints[mid][1] < weight:
                        right = mid
                    else:
                        left = mid + 1
                self.sortedPoints.insert(left,((x,y), weight))

                if progressBar != None:
                    progress += 1
                    progressBar.setValue(progress)
                
            self.bestPoint = self.sortedPoints[0][0]
            self.sortedPoints = [((x,y),w)  for ((x,_),w) in self.sortedPoints[:-1] for y in range(self.region.upPointCoord[1], self.region.downPointCoord[1]+1, self.step)]
            
        else:
            nods = self.region.createNods(self.step)
            if progressBar != None:
                progressBar.setMaximum(len(nods))
            
            for x, y in nods:
                if y-self.radius < 0 or x-self.radius < 0 or y+self.radius+1>self.images.shape[0] or x+self.radius+1>self.images.shape[1]:
                    continue
                R, G, B = self.images.getMeanRGB(x, y, self.radius).T
                
                R0 = np.repeat(np.mean(R[:self.baseline]), repeats=self.images.lenght)
                G0 = np.repeat(np.mean(G[:self.baseline]), repeats=self.images.lenght)
                B0 = np.repeat(np.mean(B[:self.baseline]), repeats=self.images.lenght)

                L = np.sqrt(R**2 + G**2 + B**2)
                L0 = np.sqrt(R0**2 + G0**2 + B0**2)

                if self.formulaKey == 0:
                    S = np.sqrt((R/L - R0/L0)**2 + (G/L - G0/L0)**2 + (B/L - B0/L0)**2)
                elif self.formulaKey == 1:
                    S = np.abs(R/L - R0/L0) + np.abs(G/L - G0/L0) + np.abs(B/L - B0/L0)
                smooth_S = self.smoothFFT(S, order=self.npts)
                weight = weightFunc(smooth_S)

                left = 0
                right = len(self.sortedPoints)
                while left < right:
                    mid = (left + right) // 2
                    if self.sortedPoints[mid][1] < weight:
                        right = mid
                    else:
                        left = mid + 1
                self.sortedPoints.insert(left,((x,y), weight))

                if progressBar != None:
                    progress += 1
                    progressBar.setValue(progress)

            self.bestPoint = self.sortedPoints[0][0]
            self.sortedPoints.pop()

    def getDataInPoint(self, point):
        x, y = point
        R, G, B = self.images.getMeanRGB(x, y, self.radius).T
            
        R0 = np.repeat(np.mean(R[:self.baseline]), repeats=self.images.lenght)
        G0 = np.repeat(np.mean(G[:self.baseline]), repeats=self.images.lenght)
        B0 = np.repeat(np.mean(B[:self.baseline]), repeats=self.images.lenght)

        L = np.sqrt(R**2 + G**2 + B**2)
        L0 = np.sqrt(R0**2 + G0**2 + B0**2)

        if self.formulaKey == 0:
            S = np.sqrt((R/L - R0/L0)**2 + (G/L - G0/L0)**2 + (B/L - B0/L0)**2)
        elif self.formulaKey == 1:
            S = np.abs(R/L - R0/L0) + np.abs(G/L - G0/L0) + np.abs(B/L - B0/L0)
        smooth_S = self.smoothFFT(S, order=self.npts)

        RG = np.abs((R/L - R0/L0) - (G/L - G0/L0))
        GB = np.abs((G/L - G0/L0) - (B/L - B0/L0))
        BR = np.abs((B/L - B0/L0) - (R/L - R0/L0))

        differences = np.array([RG, GB, BR])
        flag = [sum(diff) == max(sum(RG), sum(GB), sum(BR)) for diff in differences]
        biggestDifference = differences[flag][0]

        return R, G, B, S, smooth_S, np.array(['R-G', 'G-B', 'B-R'])[flag][0], biggestDifference


def combineResponses(BResponses, formulaKey=0):
    multyResponse = np.zeros(BResponses[0].images.lenght)
    for response in BResponses:
        biggestDifference = response.getDataInPoint(response.bestPoint)[-1]
        if formulaKey == 0:
            multyResponse += biggestDifference**2
        elif formulaKey == 1:
            multyResponse += np.abs(biggestDifference)
            
    if formulaKey == 0: return np.sqrt(multyResponse)

    return multyResponse
            
            


    
if __name__ == "__main__":
    print(0)
    # file_list = [file for file in os.listdir() if file.endswith('.jpg')]
    # imgs = Images(file_list)
    # resp = BestResponse(imgs, Rectangle((100,100),(200,200)))
    # # resp.averagedImagesMode = True
    # # start = time.time()
    # # resp.sortPoints()
    # # end = time.time()
    # # print(end-start)
    # # print(resp.sortedPoints)

    # # resp.averagedImagesMode = False
    # # start = time.time()
    # # resp.sortPoints()
    # # end = time.time()
    # # print(end-start)
    # # print(len(resp.sortedPoints))

    # # plt.imshow(imgs.images[0])
    # # plt.show()

    # file_list = [file for file in os.listdir() if file.endswith('.jpg')]
    # imgs = Images(file_list)
    # resp1 = BestResponse(imgs, Rectangle((100,100),(200,200)))
    # resp2 = BestResponse(imgs, Rectangle((200,200),(300,300)))

    # #resp1.sortPoints()
    # #resp2.sortPoints()

    # #print(combineResponses([resp1, resp2], formulaKey=0))
    # rect = Rectangle((0,0),(0,0)).getBoundaries()
    # print(rect)
    # #print(imgs.getMeanRGB(100, 100,3).T)


