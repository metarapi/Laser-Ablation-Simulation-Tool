import numpy as np
import sys
import os

from PIL import Image
import noise
import random
import scipy.signal as signal
from skimage.measure import block_reduce
from skimage.metrics import structural_similarity as ssim
import time

def load_data():
    #global nuclideNames, reshaped_array, RRs, numericArray, mappingVector, mappingVectorRR, washoutProfilesAll

    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    
    # Load .npy files
    RRs = np.load(os.path.join(bundle_dir, 'RRs.npy'))
    nuclideNames = np.load(os.path.join(bundle_dir, 'nuclideNames.npy'), allow_pickle=True)
    fluenceLabels = np.load(os.path.join(bundle_dir, 'fluenceLabels.npy'), allow_pickle=True)
    numericArray = np.load(os.path.join(bundle_dir, 'numericArray.npy'))

    washoutProfilesAll = np.load(os.path.join(bundle_dir, 'washoutProfilesAll.npy'))
    reshaped_array = np.load(os.path.join(bundle_dir, 'reshaped_array.npy'))

    inputImage = np.genfromtxt(os.path.join(bundle_dir, 'Vermeer.csv'), delimiter=',')
    craterProfile = np.genfromtxt(os.path.join(bundle_dir, 'BPn.csv'), delimiter=',')

    # Mapping vectors
    mappingVector = list(range(len(numericArray)))
    mappingVectorRR = list(range(len(RRs)))

    return {
        "RRs": RRs,
        "nuclideNames": nuclideNames,
        "fluenceLabels": fluenceLabels,
        "numericArray": numericArray,
        "washoutProfilesAll": washoutProfilesAll,
        "reshaped_array": reshaped_array,
        "mappingVector": mappingVector,
        "mappingVectorRR": mappingVectorRR,
        "inputImage": inputImage,
        "craterProfile": craterProfile
        }

def generateImage():
    # Generate 2D perlin noise
    size = 256
    scale = 100.0
    octaves = 6
    persistence = 0.5
    lacunarity = 2.0
    seed = random.randint(0, 100)
    world = np.zeros((size, size))
    for i in range(size):
        for j in range(size):
            world[i][j] = noise.pnoise2(i/scale, 
                                        j/scale,
                                        octaves=octaves, 
                                        persistence=persistence, 
                                        lacunarity=lacunarity, 
                                        repeatx=size, 
                                        repeaty=size, 
                                        base=seed)
    # Normalize the noise
    world = (world + 1) / 2
    world = (world * 255).astype(np.uint8)
    # Apply a colormap
    img = Image.fromarray(world, 'L')
    return img

"""
import time
def simulateAblation(*args, **kwargs):
    time.sleep(5)
    return np.zeros((100, 100)), np.zeros((100, 100)), 0.8, "nuclide"    
"""
def generateBeamProfile(n=10, beam=20):
    # Generates a round beam profile
    beam = 20
    n = n
    Threshold = np.exp(1)**-2

    sigma = round(beam/2)
    X, Y = np.meshgrid(np.arange(-beam/2, beam/2 + 1), np.arange(-beam/2, beam/2 + 1))
    t = np.sqrt(X**2 + Y**2)
    BP_round = np.exp(-2 * (t**n / sigma**n))

    # Crater profile
    BPn = BP_round - Threshold * np.max(BP_round)
    BPn = BPn / np.max(BPn)
    BPn[BPn < 0] = 0
    return BPn

def simulateAblation(inputImage, craterProfile, washoutProfilesAll, nuclideNames, repetitionRate, W=0, C_sample = 500, fluence = 0, dosage = 10, scanningSpeed = 2000, flickerNoise = 5, useRR=False):
    try:
        #bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))

        #inputImage = np.genfromtxt(os.path.join(bundle_dir, 'Vermeer.csv'), delimiter=',')
        #craterProfile = np.genfromtxt(os.path.join(bundle_dir, 'BPn.csv'), delimiter=',')

        # Fixed (for now) inputs
        #inputImage = np.genfromtxt('Vermeer.csv', delimiter=',')
        #craterProfile = np.genfromtxt('BPn.csv', delimiter=',')
        beamSize = 20 # um
        #flickerNoise = 5 # %
        dwellTime = 3 # ms
        C_washout = 100 # ppm

        # Import data
        #washoutProfilesAll = np.load(os.path.join(bundle_dir, 'washoutProfilesAll.npy'))
        #nuclideNames = np.load(os.path.join(bundle_dir, 'nuclideNames.npy'), allow_pickle=True)
        #fluenceLabels = np.load(os.path.join(bundle_dir, 'fluenceLabels.npy'), allow_pickle=True)

        #washoutProfilesAll = np.load('washoutProfilesAll.npy')
        #nuclideNames = np.load('nuclideNames.npy')
        #fluenceLabels = np.load('fluenceLabels.npy')

        # Selectable inputs
        # W = 14 # Nuclide index
        # C_sample = 500  # in ppm
        # fluence = 15 # Fluence index
        # dosage = 10
        # scanningSpeed = 2000 # Lateral scanning speed in µm/s
        nuclide = nuclideNames[W]

        # print("Scanning Speed (input):", scanningSpeed)
        # print("Repetition Rate (input):", repetitionRate)

        if useRR:
            scanningSpeed = round(repetitionRate * beamSize / dosage) # Scanning speed µm/s
        else:
            repetitionRate = round(scanningSpeed * dosage / beamSize) # Repetition rate in Hz

        print("Nuclide:", nuclide)
        print("Use Repetition Rate:", useRR)
        print("Repetition Rate:", repetitionRate)
        print("Scanning Speed:", scanningSpeed)
        print("Dosage:", dosage)

        # Obtain washout profile based on selected nuclide and fluence
        washoutProfile = washoutProfilesAll[:,W,fluence]
        responseCurve0 = (dwellTime / 1000) * washoutProfile

        # Normalize image
        normalizedInputImage = inputImage / np.max(inputImage)

        # Horizontal and vertical step size
        k = int(beamSize / dosage)
        m = int(beamSize)

        # Double convolution (sampling blur and smear)
        convolved = signal.convolve2d(normalizedInputImage, craterProfile, mode='full') # Equivalent to MATLAB's conv2
        # Normalize convolved image
        normalizedConvolved = convolved / np.max(convolved)
        # Subsample convolved image
        normalizedConvolvedNoNoise = normalizedConvolved[m-1::m, k-1::k]

        # Resample response curve
        numSamples = round(100 * 1000 / repetitionRate) # Number of samples in the response curve
        responseCurve = (1000 / repetitionRate) * (1 / dwellTime) * signal.resample_poly(responseCurve0, 300, numSamples) # resample_poly is analogous to resample in MATLAB

        # Convert to 2-D by adding a new axis
        responseCurve2D = responseCurve[np.newaxis,:] 

        # Smear the image
        smearedImageRaw = signal.convolve2d(normalizedConvolvedNoNoise, responseCurve2D, mode='full') # Equivalent to MATLAB's conv2

        # Average every dosage shots into a single pixel
        blockSize = (1, dosage)
        smearedImage = (C_sample / C_washout) * dosage * block_reduce(smearedImageRaw, blockSize, np.mean) # Equivalent to MATLAB's blockproc

        # Set negative values and NaNs to zero
        smearedImage[smearedImage < 0] = 0
        smearedImage[np.isnan(smearedImage)] = 0

        # Simulate applying Poisson noise to an image
        smearedImagePNoise = np.random.poisson(smearedImage)

        #smearedImagePNoise = np.random.poisson(smearedImage / 1e12) * 1e12
        # Apply additional noise, which is a combination of Poisson noise and Gaussian noise
        SmearedImagePFNoise = smearedImagePNoise + np.random.randn(*smearedImagePNoise.shape) * (smearedImagePNoise * flickerNoise / 100)
        # Normalize the final noisy image
        SmearedImagePFNoiseNorm = SmearedImagePFNoise / np.max(SmearedImagePFNoise)

        # Create a normalized reference image for SSIM calculation
        referenceImage = block_reduce(normalizedInputImage, (beamSize, beamSize), np.mean)
        referenceImage = referenceImage / np.max(referenceImage)

        # Image shifting
        add = np.zeros((SmearedImagePFNoiseNorm.shape[0], 200))
        SmearedImagePFNoiseNorm = np.hstack([SmearedImagePFNoiseNorm, add])
        shift = []
        # 21 is the size of the convolution kernel (beamSize)
        for peakShift in range(20):
            # Shift the smeared image and normalize it
            SmearedImagePFNoiseNormTmp = SmearedImagePFNoiseNorm[:150, peakShift:150+peakShift]
            SmearedImagePFNoiseNormTmp = SmearedImagePFNoiseNormTmp / np.max(SmearedImagePFNoiseNormTmp)
            # Calculate SSIM and store it
            ssimval = ssim(SmearedImagePFNoiseNormTmp, referenceImage,data_range=1.0)
            shift.append((peakShift, ssimval))

        # Determine the shift that maximizes the SSIM
        shift = np.array(shift)
        I = np.argmax(shift[:, 1])

        # Obtain the maximum SSIM
        max_ssim = np.max(shift[:, 1])

        # Shift the smeared image
        SmearedImagePFNoiseNormFinal = SmearedImagePFNoiseNorm[:150, I:150+I]

        # Calculate mapping time [s]
        mapTime = round(150*3000*dosage/(beamSize*repetitionRate))

        return referenceImage, SmearedImagePFNoiseNormFinal, max_ssim, nuclide, mapTime
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None, None, None


import time  # Ensure time is imported at the beginning of your script

def simulateAblationTimed(inputImage, craterProfile, washoutProfilesAll, nuclideNames, repetitionRate, W=0, C_sample = 500, fluence = 0, dosage = 10, scanningSpeed = 2000, flickerNoise = 5, useRR=False):
    try:
        beamSize = 20 # um
        dwellTime = 3 # ms
        C_washout = 100 # ppm

        nuclide = nuclideNames[W]

        if useRR:
            scanningSpeed = round(repetitionRate * beamSize / dosage) # Scanning speed µm/s
        else:
            repetitionRate = round(scanningSpeed * dosage / beamSize) # Repetition rate in Hz

        print("Nuclide:", nuclide)
        print("Use Repetition Rate:", useRR)
        print("Repetition Rate:", repetitionRate)
        print("Scanning Speed:", scanningSpeed)
        print("Dosage:", dosage)

        # Obtain washout profile based on selected nuclide and fluence
        washoutProfile = washoutProfilesAll[:,W,fluence]
        responseCurve0 = (dwellTime / 1000) * washoutProfile

        # Normalize image
        normalizedInputImage = inputImage / np.max(inputImage)

        # Horizontal and vertical step size
        k = int(beamSize / dosage)
        m = int(beamSize)

        conT = time.time()
        # Double convolution (sampling blur and smear)
        convolved = signal.fftconvolve(normalizedInputImage, craterProfile, mode='full')
        convolved = signal.convolve2d(normalizedInputImage, craterProfile, mode='full') 
        print(f"Convolution duration (normal): {time.time() - conT:.3f}")
        # Normalize convolved image
        normalizedConvolved = convolved / np.max(convolved)
        # Subsample convolved image
        normalizedConvolvedNoNoise = normalizedConvolved[m-1::m, k-1::k]

        # Resample response curve
        numSamples = round(100 * 1000 / repetitionRate) # Number of samples in the response curve
        responseCurve = (1000 / repetitionRate) * (1 / dwellTime) * signal.resample_poly(responseCurve0, 300, numSamples) # resample_poly is analogous to resample in MATLAB

        # Convert to 2-D by adding a new axis
        responseCurve2D = responseCurve[np.newaxis,:] 

        # Smear the image
        smearedImageRaw = signal.convolve2d(normalizedConvolvedNoNoise, responseCurve2D, mode='full') # Equivalent to MATLAB's conv2

        # Average every dosage shots into a single pixel
        blockSize = (1, dosage)
        smearedImage = (C_sample / C_washout) * dosage * block_reduce(smearedImageRaw, blockSize, np.mean) # Equivalent to MATLAB's blockproc

        # Set negative values and NaNs to zero
        smearedImage[smearedImage < 0] = 0
        smearedImage[np.isnan(smearedImage)] = 0

        # Simulate applying Poisson noise to an image
        smearedImagePNoise = np.random.poisson(smearedImage)

        #smearedImagePNoise = np.random.poisson(smearedImage / 1e12) * 1e12
        # Apply additional noise, which is a combination of Poisson noise and Gaussian noise
        SmearedImagePFNoise = smearedImagePNoise + np.random.randn(*smearedImagePNoise.shape) * (smearedImagePNoise * flickerNoise / 100)
        # Normalize the final noisy image
        SmearedImagePFNoiseNorm = SmearedImagePFNoise / np.max(SmearedImagePFNoise)

        # Create a normalized reference image for SSIM calculation
        referenceImage = block_reduce(normalizedInputImage, (beamSize, beamSize), np.mean)
        referenceImage = referenceImage / np.max(referenceImage)

        # Image shifting
        add = np.zeros((SmearedImagePFNoiseNorm.shape[0], 200))
        SmearedImagePFNoiseNorm = np.hstack([SmearedImagePFNoiseNorm, add])
        shift = []
        # 21 is the size of the convolution kernel (beamSize)
        for peakShift in range(1, 21):
            # Shift the smeared image and normalize it
            SmearedImagePFNoiseNormTmp = SmearedImagePFNoiseNorm[:150, peakShift:150+peakShift]
            SmearedImagePFNoiseNormTmp = SmearedImagePFNoiseNormTmp / np.max(SmearedImagePFNoiseNormTmp)
            # Calculate SSIM and store it
            ssimval = ssim(SmearedImagePFNoiseNormTmp, referenceImage,data_range=1.0)
            shift.append((peakShift, ssimval))

        # Determine the shift that maximizes the SSIM
        shift = np.array(shift)
        I = np.argmax(shift[:, 1])

        # Obtain the maximum SSIM
        max_ssim = np.max(shift[:, 1])

        # Shift the smeared image
        SmearedImagePFNoiseNormFinal = SmearedImagePFNoiseNorm[:150, I:150+I]

        # Calculate mapping time [s]
        mapTime = round(150*3000*dosage/(beamSize*repetitionRate))

        # Final time print
        endTime = time.time()

        return referenceImage, SmearedImagePFNoiseNormFinal, max_ssim, nuclide, mapTime
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None, None, None
