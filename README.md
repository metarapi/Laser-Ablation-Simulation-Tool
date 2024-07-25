# Laser Ablation ICPMS Simulation Tool

This application simulates the process of LA-ICP-TOFMS mapping, focusing on the visualization of experimental washout profiles for 38 nuclides [T. Van Helden et al., Anal. Chim. Acta 1287 (2024) 342089](https://www.sciencedirect.com/science/article/abs/pii/S0003267023013107), and their impact on image quality under various user-selectable mapping conditions (dosage, lateral scanning speed, repetition rate, system noise, and concentration). The application highlights the effects of image smear and noise induced by the washout profiles, and the user can explore the image quality implications through the Structural Similarity Index (SSIM), providing a quantitative measure of image quality degradation. Built with Python, the application leverages customtkinter for an interactive user interface and matplotlib for comprehensive plotting capabilities. 

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Using the Prebuilt Version

If you prefer to use the prebuilt version of the application, follow these steps:

1. Download the latest release from the [Releases](https://github.com/metarapi/Laser-Ablation-Simulation-Tool/releases) page.
2. Unzip the downloaded file to your desired location.
3. Run the executable `AblationSim.exe` from the command line or double-click it in your file explorer.

### Building from Source

If you'd like to build the application from source, here are the steps:

#### Prerequisites

Before you begin, ensure you have the following installed:
- Python (version 3.10.6 or higher)
- Nuitka (version 2.3.11 or higher)

Additionally, you will need to install the required Python dependencies listed in `requirements.txt`.

You can install these dependencies using pip:

pip install -r requirements.txt

After installing the prerequisites, you can proceed with the Nuitka build process as described:

1. Clone the repository to your local machine:

```bash
git clone https://github.com/metarapi/Laser-Ablation-Simulation-Tool.git
```

2. Navigate to the project directory

3. Run the build command:

```bash
nuitka --windows-disable-console --standalone --enable-plugin=tk-inter --windows-icon-from-ico=icon.ico --include-data-file=icon.ico=./icon.ico --include-data-file=RRs.npy=./RRs.npy --include-data-file=nuclideNames.npy=./nuclideNames.npy --include-data-file=fluenceLabels.npy=./fluenceLabels.npy --include-data-file=numericArray.npy=./numericArray.npy --include-data-file=washoutProfilesAll.npy=./washoutProfilesAll.npy --include-data-file=reshaped_array.npy=./reshaped_array.npy --include-data-file=Vermeer.csv=./Vermeer.csv --include-data-file=BPn.csv=./BPn.csv --include-data-file=cancel.png=./cancel.png AblationSim.py
```

## Third-Party Libraries

This application uses `customtkinter`, which is licensed under the MIT License.

### customtkinter

