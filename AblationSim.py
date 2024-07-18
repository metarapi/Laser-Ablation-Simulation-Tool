import numpy as np
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from tktooltip import ToolTip
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from util import load_data, generateImage, generateBeamProfile, simulateAblation
from CTkSpinbox import *
import multiprocessing
import math
from tkinter import PhotoImage

# Wrapper for multiprocessing
def simulateAblationWrapper(inputImage, craterProfile, washoutProfilesAll, nuclideNames, repetitionRate, W, C_sample, fluence, dosage, scanningSpeed, flickerNoise, useRR, resultQueue):
    result = simulateAblation(inputImage, craterProfile, washoutProfilesAll, nuclideNames, repetitionRate=repetitionRate, W=W, C_sample=C_sample, fluence=fluence, dosage=dosage, scanningSpeed=scanningSpeed, flickerNoise=flickerNoise, useRR=useRR)
    resultQueue.put(result)

class WashoutApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.data = load_data()

        # Initialize the variables

        self.RRs, self.nuclideNames, self.fluenceLabels, self.numericArray, self.washoutProfilesAll, self.reshaped_array, self.mappingVector, self.mappingVectorRR, self.inputImage, self.craterProfile = self.unpack_data()

        self.currentElement = 0 # W in the simulateAblation function
        self.currentFluence = 0 # fluence in the simulateAblation function
        self.currentRR = 0 # repetition rate in the simulateAblation function

        self.switch_var = ctk.StringVar(value="off")
        self.colormapCurrent = ctk.StringVar(value=" Gray ")
        self.useCustomBeamProfile_var = ctk.StringVar(value="off")

        self.useRR = ctk.BooleanVar(value = True)

        self.repetitionRate = ctk.IntVar(value=1000) # Can be derived
        self.C_sample = ctk.IntVar(value=500) # Sample concentration in ppm
        self.dosage = ctk.IntVar(value=10)
        self.previousDosage = ctk.IntVar(value=10)
        self.scanningSpeed = ctk.IntVar(value=2000) # Scanning speed in um/s
        self.previousScanningSpeed = ctk.IntVar(value=2000)
        self.flickerNoise = ctk.IntVar(value=5) # Flicker noise in %, advanced setting
        
        # Save the default crater profile
        self.craterProfileDefault = self.craterProfile

        # Supergaussian order n
        self.n = ctk.DoubleVar(value=10)

        self.title("Ablation Simulation")
        self.geometry("1000x800")
        self.configure(bg_color='#2b2b2b')  # Set the background color of the main window to gray
        self.iconbitmap('icon.ico') # Set the icon of the window


        main_frame = ctk.CTkFrame(self, fg_color='#2b2b2b')
        main_frame.pack(fill=ctk.BOTH, expand=1)

        # Create a tab view (tabbed interface)
        self.tabview = ctk.CTkTabview(master=main_frame, anchor=ctk.NW, corner_radius=10, fg_color="#2b2b2b", bg_color="#2b2b2b")
        self.tabview.pack(fill=ctk.BOTH, expand=1, padx=10, pady=10)

        # Add tabs to the tab view
        self.tabview.add("Washout Profiles")
        self.tabview.add("Image Quality")
        #self.tabview.add("Test tab")

        # Create frames for each tab
        self.tab1 = self.tabview.tab("Washout Profiles")
        self.tab2 = self.tabview.tab("Image Quality")

        # Add content to the first tab
        self.setup_tab1()

        # Add content to the second tab
        self.setup_tab2()

        #from util import simulateAblation

    def unpack_data(self):
        keys = ["RRs", "nuclideNames", "fluenceLabels", "numericArray", "washoutProfilesAll", "reshaped_array", "mappingVector", "mappingVectorRR", "inputImage", "craterProfile"]
        return [self.data[key] for key in keys]

    def setup_tab1(self):
        # Create a left frame for controls and a right frame for the plot
        left_frame = ctk.CTkFrame(self.tab1, width=200, fg_color='#2b2b2b')
        left_frame.pack(side=ctk.LEFT, fill=ctk.Y, padx=10, pady=10)

        # Fixed size for the right frame
        right_frame = ctk.CTkFrame(self.tab1, width=800, height=800, fg_color='#2b2b2b')
        right_frame.pack(side=ctk.RIGHT, padx=10, pady=10)
        right_frame.pack_propagate(0)  # Prevent the frame from resizing

        # Add the plot to the right frame
        self.figure = Figure(facecolor='#2b2b2b')  # Match the figure's background color with the app
        self.canvas = FigureCanvasTkAgg(self.figure, master=right_frame)
        self.axes = self.figure.add_subplot(111, facecolor='#2b2b2b')  # Match the axes' background color

        self.axes.set_xlabel("Signal (cps)")
        self.axes.set_ylabel("Time (ms)")
        self.canvas.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # Add a title above the combo box
        ctk.CTkLabel(left_frame, 
                     text="Nuclide", 
                     font=("Helvetica", 15),
                     justify="left",
                     fg_color='#2b2b2b', 
                     anchor="nw"
                     ).pack(fill=ctk.X, pady=0, padx=5)

        # Add controls to the left frame
        self.comboBox = ctk.CTkComboBox(left_frame, values=self.nuclideNames, state="readonly", command=self.comboBox_currentIndexChanged)
        self.comboBox.set(self.nuclideNames[0])
        self.comboBox.pack(pady=0)

        self.verticalSlider = ctk.CTkSlider(left_frame, from_=min(self.mappingVector), to=max(self.mappingVector), orientation="vertical",
                                            command=self.F_slider_value_changed)
        self.verticalSlider.pack(pady=10, fill=ctk.Y, expand=1)
        self.verticalSlider.set(min(self.mappingVector))  # Initialize the slider to the minimum value

        # Add labels at the bottom of the left frame
        label_frame = ctk.CTkFrame(left_frame)
        label_frame.pack(side=ctk.BOTTOM, pady=10)

        self.label = ctk.CTkLabel(label_frame, text="Fluence = 0.07 J cm\u207B\u00B2", font=("Helvetica", 15))
        self.label.pack()

        self.plot_data(self.currentElement, self.currentFluence)

    def setup_tab2(self):
        # Step 1: Create a Frame for the Second Tab
        tab2_frame1 = ctk.CTkFrame(master=self.tab2, width=167, fg_color='#2b2b2b')
        tab2_frame1.pack(side='left', padx=5, pady=5, fill='y', expand=False)
        tab2_frame1.pack_propagate(False)

        conditionsStandard_frame = ctk.CTkFrame(tab2_frame1, fg_color='#333333')
        conditionsStandard_frame.pack(side='top', padx=5, pady=5, fill='y', expand=True)

        switchFrameAdvanced = ctk.CTkFrame(tab2_frame1, height = 60 ,fg_color='#2b2b2b')
        switchFrameAdvanced.pack(side='bottom', padx=5, pady=5, fill='y', expand=False)        
        switchFrameAdvanced.pack_propagate(False)

        conditionsAdvanced_frame = ctk.CTkFrame(tab2_frame1, fg_color='#333333')
        conditionsAdvanced_frame.pack(side='top', padx=5, pady=5, fill='both', expand=True)
        conditionsAdvanced_frame.pack_propagate(False)
        conditionsAdvanced_frame.pack_forget()

        tab2_frame2 = ctk.CTkFrame(master=self.tab2, width=200, fg_color='#2b2b2b')
        tab2_frame2.pack(side='right', padx=5, pady=5, fill='both', expand=True)

        self.frame2_progressBar = ctk.CTkFrame(tab2_frame2, height=20, fg_color='#2b2b2b')
        self.frame2_progressBar.pack(side='top', padx=5, pady=0, fill='x', expand=False)
        self.frame2_progressBar.pack_propagate(False)

        frame2_upper = ctk.CTkFrame(tab2_frame2, height=40, fg_color='#2b2b2b')
        frame2_upper.pack(side='top', padx=5, pady=0, fill='x', expand=False)
        frame2_upper.pack_propagate(False)

        frame2_mid = ctk.CTkFrame(tab2_frame2, fg_color='#2b2b2b')
        frame2_mid.pack(side='top', padx=5, pady=5, fill='both', expand=True)

        frame2_labels = ctk.CTkFrame(tab2_frame2, height=40, fg_color='#2b2b2b')
        frame2_labels.pack(side='top', padx=5, pady=0, fill='x', expand=False)
        frame2_labels.pack_propagate(False)

        frame2_labels.grid_rowconfigure(0, weight=1)
        frame2_labels.grid_columnconfigure(0, weight=1)
        frame2_labels.grid_columnconfigure(1, weight=1)

        frame2_lower = ctk.CTkFrame(tab2_frame2, height=75, fg_color='#2b2b2b')
        frame2_lower.pack(side='bottom', padx=5, pady=5, fill='x', expand=False)

        # Add two subframes to the upper frame using a grid layout
        frame2_upper.grid_columnconfigure(0, weight=1)
        #frame2_upper.grid_columnconfigure(1, weight=1)
        frame2_upper.grid_rowconfigure(0, weight=1)
        #frame2_upper.grid_rowconfigure(1, weight=0)

        subframe3 = ctk.CTkFrame(frame2_upper, height = 50, fg_color='#333333')
        subframe3.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')

        subframe3.grid_rowconfigure(0, weight=1)
        subframe3.grid_columnconfigure(0, weight=1)
        subframe3.grid_columnconfigure(1, weight=1)

        self.SSIMLabel = ctk.CTkLabel(subframe3, text="SSIM:     ", font=("Helvetica", 18), text_color="#FFFFFF",  anchor="center")
        self.MappingTimeLabel = ctk.CTkLabel(subframe3, text="Mapping Time:     ", font=("Helvetica", 18), text_color="#FFFFFF",  anchor="center")
        self.SSIMLabel.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.MappingTimeLabel.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

        # Reference image frame
        subframe1 = ctk.CTkFrame(frame2_labels, height = 100, fg_color='#333333')
        subframe1.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        # Reference image label
        ctk.CTkLabel(subframe1, text="Reference Image", font=("Helvetica", 20), text_color="#FFFFFF").pack(side='top', padx=5, pady=5)

        # Smearred image frame
        subframe2 = ctk.CTkFrame(frame2_labels, height = 100, fg_color='#333333')
        subframe2.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
        # Smeared image label
        ctk.CTkLabel(subframe2, text="Simulated Image", font=("Helvetica", 20), text_color="#FFFFFF").pack(side='top', padx=5, pady=5)

        ctk.CTkLabel(frame2_lower, text="Colormap", font=("Helvetica", 16), text_color="#FFFFFF").pack(side='left', padx=(5, 8), pady=16)

        self.colorMapToggle = ctk.CTkSegmentedButton(frame2_lower, values=[" Gray ", " Inferno ", " Viridis "],
                                                            command=self.change_colormap, font=("Helvetica", 12),
                                                            variable=self.colormapCurrent)
        self.colorMapToggle.pack(side='left', padx=(5, 8), pady=16)
        self.colorMapToggle.set(" Gray ")        

        # Add a button to the lower frame
        self.runSimulationButton = ctk.CTkButton(frame2_lower, text="Run Simulation", font=("Helvetica", 16), command=self.executeSimulation)
        self.runSimulationButton.pack(side='right', padx=(8, 5), pady=16)

        # Use grid layout for the frames that will contain the figures
        frame2_mid.grid_columnconfigure(0, weight=1)
        frame2_mid.grid_columnconfigure(1, weight=1)
        frame2_mid.grid_rowconfigure(0, weight=1)
        frame2_mid.grid_rowconfigure(1, weight=0)

        figure1_frame = ctk.CTkFrame(frame2_mid, fg_color='#000000')
        figure1_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

        figure2_frame = ctk.CTkFrame(frame2_mid, fg_color='#000000')
        figure2_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

        # Initial placeholder
        #img = generateImage()
        img = np.ones((100, 100))

        # Create the first figure
        self.fig1 = Figure(facecolor='#2b2b2b')
        ax1 = self.fig1.add_subplot()  # Create a single plot for the first figure
        ax1.imshow(img, cmap='gray')
        ax1.axis('off')
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=figure1_frame)
        self.canvas1.draw()
        self.canvas1.get_tk_widget().pack(fill='both', expand=True)
        self.canvas1.get_tk_widget().pack_propagate(True)

        # Create the second figure
        self.fig2 = Figure(facecolor='#2b2b2b')
        ax2 = self.fig2.add_subplot()  # Create a single plot for the second figure
        ax2.imshow(img, cmap='gray')
        ax2.axis('off')
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=figure2_frame)
        self.canvas2.draw()
        self.canvas2.get_tk_widget().pack(fill='both', expand=True)
        self.canvas2.get_tk_widget().pack_propagate(True)

        spinerBoxfont = ('Helvetica', 12, 'bold')
        spinerBoxLabelFont = ('Helvetica', 14)

        # Standard conditions frame

        # This subframe holds the toggle button for the RR and SS
        toggleRRSSFrame = ctk.CTkFrame(conditionsStandard_frame, height = 80, width= 50, fg_color='#333333')
        toggleRRSSFrame.grid(row=0, column=0, padx=0, pady=0, sticky='ew')

        toggleRRSSLabel = ctk.CTkLabel(toggleRRSSFrame, text='Toggle Input Parameter', font=spinerBoxfont)
        toggleRRSSLabel.pack(pady=0, padx = 0, side='top', anchor='center')

        # Add a segmented button to the frame to toggle between Repetition Rate and Scanning Speed
        self.toggleRRSSSegmentedButton = ctk.CTkSegmentedButton(toggleRRSSFrame, values=["Repetition\n Rate", "Scanning\n Speed"],
                                                            command=self.toggleRRSS, font=("Helvetica", 12))
        self.toggleRRSSSegmentedButton.pack(pady=(0,10), padx = 0, side='top', anchor='center')
        self.toggleRRSSSegmentedButton.set("Repetition\n Rate")

        self.spinboxRepetitionRateLabel = ctk.CTkLabel(conditionsStandard_frame, text_color='#2FA572', text='Repetition Rate [Hz]', font=spinerBoxLabelFont)
        self.spinboxRepetitionRateLabel.grid(row=1, column=0, padx=5, pady=0, sticky='ew')

        self.spinboxRepetitionRate = CTkSpinbox(conditionsStandard_frame,
                            start_value=1000,
                            min_value=10,
                            max_value=1000,
                            step_value=1,
                            scroll_value=20,
                            font = spinerBoxfont,
                            variable=self.repetitionRate,
                            command=self.changeScanSpeed)
        self.spinboxRepetitionRate.grid(row=2, column=0, padx=5, pady=(0,5), sticky='ew')

        ToolTip(self.spinboxRepetitionRate, msg="Use mouse scroll for larger increments", delay=1, follow=True,
            parent_kwargs={"bg": "#2FA572", "padx": 1, "pady": 1},
            fg="#ffffff", bg="#1c1c1c", padx=3, pady=3)

        # This one controls the scanning speed
        self.spinboxScanningSpeedLabel = ctk.CTkLabel(conditionsStandard_frame, text_color='#888888',text='Scanning Speed [μm/s]', font=spinerBoxLabelFont)
        self.spinboxScanningSpeedLabel.grid(row=3, column=0, padx=5, pady=0, sticky='ew')

        self.spinboxScanningSpeed = CTkSpinbox(conditionsStandard_frame,
                            start_value=2000,
                            min_value=10,
                            max_value=10000,
                            step_value=10,
                            scroll_value=50,
                            text_color='#888888',
                            font = spinerBoxfont,
                            state = 'disabled',
                            variable=self.scanningSpeed,
                            command=self.changeRepetitionRate)
        self.spinboxScanningSpeed.grid(row=4, column=0, padx=5, pady=(0,5), sticky='ew')

        ToolTip(self.spinboxScanningSpeed, msg="Use mouse scroll for larger increments", delay=1, follow=True,
            parent_kwargs={"bg": "#2FA572", "padx": 1, "pady": 1},
            fg="#ffffff", bg="#1c1c1c", padx=3, pady=3)

        # This one controls the sample concentration
        spinboxConcentrationLabel = ctk.CTkLabel(conditionsStandard_frame, text='Concentration [ppm]', font=spinerBoxLabelFont)
        spinboxConcentrationLabel.grid(row=5, column=0, padx=5, pady=0, sticky='ew')

        spinboxConcentration = CTkSpinbox(conditionsStandard_frame,
                            start_value=500,
                            min_value=1,
                            max_value=10000,
                            scroll_value=50,
                            step_value=1,
                            font = spinerBoxfont,
                            variable=self.C_sample)
        spinboxConcentration.grid(row=6, column=0, padx=5, pady=(0,5), sticky='ew')

        ToolTip(spinboxConcentration, msg="Use mouse scroll for larger increments", delay=1, follow=True,
            parent_kwargs={"bg": "#2FA572", "padx": 1, "pady": 1},
            fg="#ffffff", bg="#1c1c1c", padx=3, pady=3)

        # This one controls the dosage
        spinboxDosageLabel = ctk.CTkLabel(conditionsStandard_frame, text='Dosage', font=spinerBoxLabelFont)
        spinboxDosageLabel.grid(row=7, column=0, padx=5, pady=0, sticky='ew')

        self.spinboxDosage = CTkSpinbox(conditionsStandard_frame,
                            start_value=10,
                            min_value=1,
                            max_value=20,
                            scroll_value=1,
                            step_value=1,
                            font = spinerBoxfont,
                            variable=self.dosage,
                            command=self.changeDosage)
        self.spinboxDosage.grid(row=8, column=0, padx=5, pady=(0,5), sticky='ew')

        ToolTip(self.spinboxDosage, msg="Use mouse scroll for larger increments", delay=1, follow=True,
            parent_kwargs={"bg": "#2FA572", "padx": 1, "pady": 1},
            fg="#ffffff", bg="#1c1c1c", padx=3, pady=3)

        # Flicker noise
        spinboxFlickerLabel = ctk.CTkLabel(conditionsStandard_frame, text='Flicker noise [%]', font=spinerBoxLabelFont)
        spinboxFlickerLabel.grid(row=9, column=0, padx=5, pady=0, sticky='ew')

        spinboxFlicker = CTkSpinbox(conditionsStandard_frame,
                            start_value=5,
                            min_value=1,
                            max_value=20,
                            scroll_value=2,
                            step_value=1,
                            font = spinerBoxfont,
                            variable=self.flickerNoise)
        spinboxFlicker.grid(row=10, column=0, padx=5, pady=(0,5), sticky='ew')

        ToolTip(spinboxFlicker, msg="Use mouse scroll for larger increments", delay=1, follow=True,
            parent_kwargs={"bg": "#2FA572", "padx": 1, "pady": 1},
            fg="#ffffff", bg="#1c1c1c", padx=3, pady=3)

        # Advanced conditions frame

        superGaussianSwitchLabel = ctk.CTkLabel(conditionsAdvanced_frame, text='Custom Crater Profile', font=("Helvetica", 12))
        superGaussianSwitchLabel.pack(pady=5)

        # superGaussian order switch
        self.superGaussianSwitch = ctk.CTkSwitch(conditionsAdvanced_frame, 
                                                 text="", 
                                                 font=("Helvetica", 12),
                                                 variable=self.useCustomBeamProfile_var,
                                                 command=self.useCustomBeamProfileShow,
                                                 onvalue="on", offvalue="off")
        self.superGaussianSwitch.pack(pady=0, padx = 50, side='top', anchor='center')

        self.superGaussianOrderLabel = ctk.CTkLabel(conditionsAdvanced_frame, text='Super Gaussian Order (n)', font=("Helvetica", 12))
        self.superGaussianOrderLabel.pack(pady=5)

        self.nSlider = ctk.CTkSlider(conditionsAdvanced_frame, 
                                from_=2,
                                to=20,
                                number_of_steps=180,
                                fg_color='#2b2b2b',
                                bg_color='#2b2b2b',
                                command=self.useCustomBeamProfile,
                                variable=self.n)
        self.nSlider.set(10)
        self.nSlider.pack(pady=5)
        self.nSlider.pack_forget()

        self.nValueLabel = ctk.CTkLabel(conditionsAdvanced_frame, text='n = 10', font=("Helvetica", 12))
        self.nValueLabel.pack(pady=5)
        self.nValueLabel.pack_forget()

        # Frame only for the figure
        self.beamProfileFrame = ctk.CTkFrame(conditionsAdvanced_frame, height=100,fg_color='#2b2b2b')
        self.beamProfileFrame.pack(side='top', padx=5, pady=5, fill='x', expand=True)
        self.beamProfileFrame.pack_propagate(False)
        self.beamProfileFrame.pack_forget()

        # Beam profile cross section plot figure
        self.beamProfileFigure = Figure(facecolor='#333333')
        self.beamProfileAxes = self.beamProfileFigure.add_subplot(111)
        self.beamProfileAxes.axis('off')
        self.beamProfileCanvas = FigureCanvasTkAgg(self.beamProfileFigure, master=self.beamProfileFrame)
        self.beamProfileCanvas.draw()
        self.beamProfileCanvas.get_tk_widget().pack(fill='both', expand=True)
        self.beamProfileCanvas.get_tk_widget().pack_forget()

        self.profileLabel = ctk.CTkLabel(conditionsAdvanced_frame, text='Crater Profile', height=50, bg_color='#ff2255',font=("Helvetica", 12))
        self.profileLabel.pack(side='top',pady=0)
        self.profileLabel.pack_forget()

        # Add a switch to the switch frame
        self.switchAdvanced = ctk.CTkSwitch(switchFrameAdvanced, text="Advanced", font=("Helvetica", 16), command=lambda: self.switchShowAdvanced(conditionsAdvanced_frame),
                      variable=self.switch_var, onvalue="on", offvalue="off")
        #self.switchAdvanced.pack(pady=16)

    def changeRepetitionRate(self, value):
        D = self.dosage.get()
        SS = self.scanningSpeed.get()
        minSS = max(20 / D, self.spinboxScanningSpeed.min_value) # Minimum possible scanning speed (RR = 1 Hz)

        RR = round(SS / 20 * D, 1)

        if RR % 1 != 0:
            if SS > self.previousScanningSpeed.get(): # Increasing 
                RR = math.ceil(RR)
                SS = RR * 20 / D
            else: # Decreasing
                RR = math.floor(RR)
                SS = RR * 20 / D
            if SS < minSS:
                RR = 1
                SS = minSS
            self.spinboxScanningSpeed.set(int(SS))
            self.scanningSpeed.set(int(SS))

        if RR > self.spinboxRepetitionRate.max_value:
            RR = self.spinboxRepetitionRate.max_value
            # Recalculate the scanning speed
            SS = round(RR * 20 / self.dosage.get())
            # Update the scanning speed
            self.spinboxScanningSpeed.set(int(SS))
            self.scanningSpeed.set(int(SS))

        self.spinboxRepetitionRate.set(int(RR))
        self.repetitionRate.set(int(RR))
        self.previousScanningSpeed.set(int(SS))

    def changeScanSpeed(self, value):
        SS = round(self.repetitionRate.get() * 20 / self.dosage.get())
        if SS > self.spinboxScanningSpeed.max_value:
            SS = self.spinboxScanningSpeed.max_value
            # Recalculate the repetition rate
            RR = round(SS * self.dosage.get() / 20, 1)
            # Update the repetition rate
            self.spinboxRepetitionRate.set(int(RR))
            self.repetitionRate.set(int(RR))
        self.spinboxScanningSpeed.set(int(SS))
        self.scanningSpeed.set(int(SS))
        self.previousScanningSpeed.set(int(SS))

    def changeDosage(self, value):

        # Check if the dosage is in the allowed list
        allowedDosages = [1, 2, 5, 10, 20]
        dosage = self.dosage.get()
        previousDosage = self.previousDosage.get()
        if dosage not in allowedDosages:
            if dosage > previousDosage:
                idx = allowedDosages.index(previousDosage) + 1
            elif dosage < previousDosage:
                idx = allowedDosages.index(previousDosage) - 1
            dosage = allowedDosages[idx]

        self.dosage.set(dosage)
        self.previousDosage.set(dosage)
        self.spinboxDosage.set(dosage)

        # Calculate minimum possible scanning speed (minSS)
        minSS = max(20 / dosage, self.spinboxScanningSpeed.min_value)

        # Set the maximum number of iterations for the adjustment loop
        iterations_max = 10

        # Check if repetition rate (RR) input is being used
        if self.useRR:
            # Get the current repetition rate
            RR = self.repetitionRate.get()
            # Calculate the scanning speed (SS) based on the repetition rate and dosage
            SS = round(RR * 20 / dosage, 1)
            
            # Iterate to adjust RR and SS within their respective bounds
            for _ in range(iterations_max):
                # If SS exceeds its maximum, adjust RR and set SS to its maximum
                if SS > self.spinboxScanningSpeed.max_value:
                    RR = self.repetitionRate.get() * (self.spinboxScanningSpeed.max_value / SS)
                    SS = self.spinboxRepetitionRate.max_value
                # If SS is below its minimum, adjust RR and set SS to its minimum
                elif SS < self.spinboxScanningSpeed.min_value:
                    RR = self.repetitionRate.get() * (self.spinboxScanningSpeed.min_value / SS)
                    SS = self.spinboxScanningSpeed.min_value
                # Ensure RR is within its bounds
                RR = min(max(RR, self.spinboxRepetitionRate.min_value), self.spinboxRepetitionRate.max_value)

                # Check for non-whole numbers and adjuct accordingly
                if RR % 1 != 0:
                    if SS > self.previousScanningSpeed.get():
                        RR = math.ceil(RR)
                        SS = RR * 20 / dosage
                    else:
                        RR = math.floor(RR)
                        SS = RR * 20 / dosage
                    if SS < minSS:
                        RR = 1
                        SS = minSS

                # Break the loop if both RR and SS are within their bounds
                if (SS >= self.spinboxScanningSpeed.min_value and SS <= self.spinboxScanningSpeed.max_value) and (RR >= self.spinboxRepetitionRate.min_value and RR <= self.spinboxRepetitionRate.max_value):
                    break

        else:
            # Get the current scanning speed if not using RR as input
            SS = self.scanningSpeed.get()
            # Calculate the repetition rate based on scanning speed and dosage
            RR = round(SS * dosage / 20)

            # Iterate to adjust RR and SS within their respective bounds
            for _ in range(iterations_max):
                # If RR exceeds its maximum, adjust SS and set RR to its maximum
                if RR > self.spinboxRepetitionRate.max_value:
                    SS = self.scanningSpeed.get() * (self.spinboxRepetitionRate.max_value / RR)
                    RR = self.spinboxRepetitionRate.max_value
            
                # If RR is below its minimum, adjust SS and set RR to its minimum
                elif RR < self.spinboxRepetitionRate.min_value:
                    SS = self.scanningSpeed.get() * (self.spinboxRepetitionRate.min_value / RR)
                    RR = self.spinboxRepetitionRate.min_value

                # Check for non-whole numbers and adjust accordingly
                if RR % 1 != 0:
                    if SS > self.previousScanningSpeed.get():
                        RR = math.ceil(RR)
                        SS = RR * 20 / dosage
                    else:
                        RR = math.floor(RR)
                        SS = RR * 20 / dosage
                    if SS < minSS:
                        RR = 1
                        SS = minSS

                # Break the loop if both RR and SS are within their bounds
                if (SS >= self.spinboxScanningSpeed.min_value and SS <= self.spinboxScanningSpeed.max_value) and (RR >= self.spinboxRepetitionRate.min_value and RR <= self.spinboxRepetitionRate.max_value):
                    break

        # Set the adjusted values to their respective spinboxes            
        self.spinboxScanningSpeed.set(int(SS))
        self.scanningSpeed.set(int(SS))
        self.spinboxRepetitionRate.set(int(RR))
        self.repetitionRate.set(int(RR))
        self.previousScanningSpeed.set(int(SS))

    def toggleRRSS(self, value):
        if value == "Repetition\n Rate":
            self.useRR.set(True)
            SS = round(self.repetitionRate.get() * 20 / self.dosage.get())
            if SS > self.spinboxScanningSpeed.max_value:
                SS = self.spinboxScanningSpeed.max_value
                # Recalculate the repetition rate
                RR = round(SS * self.dosage.get() / 20)
                # Update the repetition rate
                self.spinboxRepetitionRate.set(RR)
            self.spinboxScanningSpeed.configure(state='disabled', text_color='#888888')
            self.spinboxScanningSpeedLabel.configure(text_color='#888888')
            self.spinboxScanningSpeed.set(SS)
            self.scanningSpeed.set(SS)
            self.spinboxRepetitionRate.configure(state='normal', text_color='#ffffff')
            self.spinboxRepetitionRateLabel.configure(text_color='#2FA572')
        else:
            self.useRR.set(False)
            RR = round(self.scanningSpeed.get() * self.dosage.get() / 20)
            if RR > self.spinboxRepetitionRate.max_value:
                RR = self.spinboxRepetitionRate.max_value
                # Recalculate the scanning speed
                SS = round(RR * 20 / self.dosage.get())
                # Update the scanning speed
                self.spinboxScanningSpeed.set(SS)
            self.spinboxScanningSpeed.configure(state='normal', text_color='#ffffff')
            self.spinboxScanningSpeedLabel.configure(text_color='#2FA572')
            self.spinboxRepetitionRate.set(RR)
            self.repetitionRate.set(RR)
            self.spinboxRepetitionRate.configure(state='disabled', text_color='#888888')
            self.spinboxRepetitionRateLabel.configure(text_color='#888888')

    def update_image(self, image, figure_number):
        if self.colormapCurrent.get() == " Gray ":
            print(self.colormapCurrent.get())
            cmap = 'gray'
        elif self.colormapCurrent.get() == " Inferno ":
            print(self.colormapCurrent.get())
            cmap = 'inferno'
        else:
            print(self.colormapCurrent.get())
            cmap = 'viridis'

        if figure_number == 1:
            # Clear the existing axes for figure 1
            self.fig1.clf()
            # Add a new subplot to fig1
            ax1 = self.fig1.add_subplot()
            # Display the new image on ax1
            ax1.imshow(image, cmap=cmap)
            ax1.axis('off')
            self.fig1.tight_layout(pad=0)
            # Redraw the canvas
            self.canvas1.draw()
        elif figure_number == 2:
            # Clear the existing axes for figure 2
            self.fig2.clf()
            # Add a new subplot to fig2
            ax2 = self.fig2.add_subplot()
            # Display the new image on ax2
            ax2.imshow(image, cmap=cmap)
            ax2.axis('off')
            self.fig2.tight_layout(pad=0)
            # Redraw the canvas
            self.canvas2.draw()

    def executeSimulation(self):
        print("Executing simulation")

        # Disable the button to prevent multiple executions
        self.runSimulationButton.configure(state="disabled", text="Running")

        # Create a progress bar and start it
        progressbar = ctk.CTkProgressBar(self.frame2_progressBar, orientation="horizontal", mode='indeterminate', determinate_speed=2)
        progressbar.pack(side='bottom', padx=5, pady=0, fill='x', expand=False)
        progressbar.start()

        # Update the SSIM and Mapping Time labels
        self.SSIMLabel.configure(text="SSIM:     ")
        self.MappingTimeLabel.configure(text="Mapping Time:     ")

        # Create a queue for communication
        resultQueue = multiprocessing.Queue()

        # Create and start a separate process
        simulationProcess = multiprocessing.Process(target=simulateAblationWrapper, args=(self.inputImage, 
                                                                                          self.craterProfile, 
                                                                                          self.washoutProfilesAll,
                                                                                          self.nuclideNames, 
                                                                                          self.repetitionRate.get(),
                                                                                          self.currentElement, 
                                                                                          self.C_sample.get(), 
                                                                                          self.currentFluence, 
                                                                                          self.dosage.get(), 
                                                                                          self.scanningSpeed.get(),
                                                                                          self.flickerNoise.get(),
                                                                                          self.useRR.get(), 
                                                                                          resultQueue))
        simulationProcess.start()

        # Check for the result in a non-blocking way
        def checkProcess():
            if not resultQueue.empty():
                result = resultQueue.get()
                # Check if the simulation was successful
                if all(item is not None for item in result):
                    referenceImage, SmearedImagePFNoiseNormFinal, max_ssim, nuclide, mapTime = result
                    self.update_image(referenceImage, 1)
                    self.update_image(SmearedImagePFNoiseNormFinal, 2)
                    # Update button text
                    self.runSimulationButton.configure(state="normal", text="Run Simulation")
                    # Remove the progress bar
                    progressbar.stop()
                    progressbar.pack_forget()
                    # Update SSIM and Mapping Time labels
                    self.SSIMLabel.configure(text="SSIM: {:.3f}".format(max_ssim))
                    self.MappingTimeLabel.configure(text="Mapping Time: {:.2f} s".format(mapTime))
                else:
                    # Handle the error case
                    self.runSimulationButton.configure(state="normal", text="Run Simulation")
                    progressbar.stop()
                    progressbar.pack_forget()
                    # Schedule the error display on the UI thread
                    self.after(0, self.show_error)
            else:
                # Re-check after some delay
                self.after(100, checkProcess)  # Assuming you're using Tkinter

        checkProcess()
    
    def show_error(self):
        # Show some error message
        CTkMessagebox(title="Error", message="The selected conditions failed to produce an output image.\nPlease select different input parameters.", icon="cancel.png")

    def switchShowAdvanced(self, container):
            # Check if the switch is on or off
            if self.switch_var.get() == "on":
                # Enable the container
                container.configure(fg_color="#333333")
                container.pack(side='top', padx=5, pady=5, fill='both', expand=True)
            else:
                # Disable the container
                container.configure(fg_color="gray")
                container.pack_forget()
                # Reset the beam profile to the default
                self.craterProfile = self.craterProfileDefault

    def change_colormap(self,value):
        # Check if the switch is on or off
        if value == " Gray ":
            # Change the colormap to 'gray'
            #self.colormap_switch.configure(text="Colormap: Inferno")
            self.fig1.get_axes()[0].images[0].set_cmap('gray')
            self.fig2.get_axes()[0].images[0].set_cmap('gray')
            self.canvas1.draw()
            self.canvas2.draw()
        elif value == " Inferno ":
            # Change the colormap to 'inferno'
            #self.colormap_switch.configure(text="Colormap: Inferno")
            self.fig1.get_axes()[0].images[0].set_cmap('inferno')
            self.fig2.get_axes()[0].images[0].set_cmap('inferno')
            self.canvas1.draw()
            self.canvas2.draw()
        else:
            # Change the colormap to 'viridis'
            #self.colormap_switch.configure(text="Colormap: Gray")
            self.fig1.get_axes()[0].images[0].set_cmap('viridis')
            self.fig2.get_axes()[0].images[0].set_cmap('viridis')
            self.canvas1.draw()
            self.canvas2.draw()

    def useCustomBeamProfileShow(self, value=None):
        if self.useCustomBeamProfile_var.get() == "on":
            self.superGaussianOrderLabel.pack()
            self.nSlider.pack()
            self.nValueLabel.pack()
            self.beamProfileFrame.pack()
            self.beamProfileCanvas.get_tk_widget().pack(fill='both', expand=True)
            self.plotBeamProfile()
            self.profileLabel.pack()
        else:
            self.superGaussianOrderLabel.pack_forget()
            self.beamProfileFrame.pack_forget()
            self.beamProfileCanvas.get_tk_widget().pack_forget()
            self.nSlider.pack_forget()
            self.nValueLabel.pack_forget()
            self.profileLabel.pack_forget()
            # Reset the beam profile to the default
            self.craterProfile = self.craterProfileDefault

    def useCustomBeamProfile(self, value=None):
        current_n_value = self.nSlider.get()
        self.nValueLabel.configure(text='n = {:.2f}'.format(current_n_value))
        # Update the beam profile
        self.craterProfile = generateBeamProfile(n=current_n_value)
        self.plotBeamProfile()

    def plotBeamProfile(self):
        # Obtain the current craterProfile
        middle = int(self.craterProfile.shape[0] // 2)
        craterProfile = -self.craterProfile[middle, :]
        self.beamProfileAxes.set_facecolor('#333333')
        self.beamProfileAxes.clear()
        self.beamProfileAxes.plot(craterProfile, color='#0a84ff', linewidth=2)
        self.beamProfileAxes.axis('off')
        self.beamProfileCanvas.draw()

    def F_slider_value_changed(self, value):
        index = int(value)
        fluence_value = self.numericArray[self.mappingVector[index]]
        self.label.configure(text='Fluence = {:.2f} J cm\u207B\u00B2'.format(fluence_value))
        self.currentFluence = index
        self.plot_data(self.currentElement, self.currentFluence)

    def comboBox_currentIndexChanged(self, event):
        selected_element = self.comboBox.get()  # Retrieve the selected element from the comboBox
        nuclideNamesList = self.nuclideNames.tolist()  # Convert numpy.ndarray to list
        self.currentElement = nuclideNamesList.index(selected_element)  # Find the index of the selected element in the list
        self.plot_data(self.currentElement, self.currentFluence)

    def plot_data(self, currentElement, currentFluence):
        # Clear the previous plot
        self.axes.clear()
        # Get the data from the washoutProfilesAll 3D array
        data = self.washoutProfilesAll[:, currentElement, currentFluence]
        
        # Set the x-axis values spaced out every 3 ms
        time = np.arange(0, data.shape[0] * 3, 3)

        # Define a color for the plot that matches customtkinter's theme
        plot_color = '#0a84ff'  # A shade of blue that complements customtkinter's default theme

        # Plot the data
        self.axes.plot(time, data, color=plot_color)

        # Set axes background to white
        self.axes.set_facecolor('#2b2b2b')
        # Set figure background to dark gray
        self.figure.patch.set_facecolor('#2b2b2b')

        # Set labels and title
        self.axes.set_xlabel('Time (ms)', color='#ffffff')
        self.axes.set_ylabel('Signal (cps)', color='#ffffff')
        self.axes.set_title('Washout Profiles', color='#ffffff')
        self.axes.tick_params(axis='x', colors='#ffffff')
        self.axes.tick_params(axis='y', colors='#ffffff')

        # Change the edge color of the plot area to white if needed
        for spine in self.axes.spines.values():
            spine.set_edgecolor('#ffffff')

        # Refresh the canvas
        self.canvas.draw()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    ctk.set_appearance_mode("Dark")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("green")  # Themes: "blue" (default), "green", "dark-blue"
    
    app = WashoutApp()
    app.mainloop()
