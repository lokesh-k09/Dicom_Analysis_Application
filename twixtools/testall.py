import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from twixtools.map_twix import map_twix

# === CONFIG ===
dat_dir = r"E:\Development\.DAT Data"

# --- QA output structure ---
qadir = os.path.join(dat_dir, "QA")
plotsdir = os.path.join(qadir, "PLOTS_PPM")
exceldir = os.path.join(qadir, "Excels")

for d in [qadir, plotsdir, exceldir]:
    os.makedirs(d, exist_ok=True)

# --- Find all .dat files ---
dat_files = glob.glob(os.path.join(dat_dir, "*.dat"))
Ndat = len(dat_files)

ppm_summary = np.zeros((3, Ndat))
fft_data_all = []
GA_labels = []

txtX = 140
SW = 1000

for i, dat_file in enumerate(dat_files):
    print(f"Processing: {dat_file}")

    twix = map_twix(dat_file)
    dwelltime = twix[0]['hdr']['MeasYaps']['sRXSPEC']['alDwellTime'][0]
    CF = twix[0]['hdr']['Dicom']['lFrequency']

    try:
        image_obj = twix[0]['image']
        imagedata = np.asarray(image_obj)
    except Exception as e:
        print(f"Skipped: image conversion failed ({e})")
        continue

    if imagedata.ndim != 3:
        print("Skipped: image data not 3D")
        continue

    nx, nc, nr = imagedata.shape
    ppmksp = imagedata.reshape((nx, nc * nr))

    # FFT & normalize
    ppmfft = np.abs(np.fft.fftshift(np.fft.ifft(ppmksp, axis=0), axes=0))
    ppmdata = np.sqrt(np.sum(ppmfft ** 2, axis=1))
    ppmdata /= np.max(ppmdata)

    fft_data_all.append(ppmdata)

    # Frequency axis
    N = ppmdata.size
    bw_per_pixel = (1e9 / (dwelltime * 256))
    total_bw = bw_per_pixel * N
    SW = total_bw
    xvals = np.linspace(-SW/2, SW/2, N)

    peakVal = np.max(ppmdata)
    peakIdx = np.argmax(ppmdata)
    halfVal = peakVal / 2
    delta_cf = round((peakIdx - N/2) * bw_per_pixel)
    CF_New = CF + delta_cf

    ppm_summary[0, i] = CF_New

    # FWHM
    leftIdx = np.where(ppmdata[:peakIdx] <= halfVal)[0]
    if leftIdx.size > 0 and leftIdx[-1] < peakIdx:
        leftIdx = leftIdx[-1]
        xLeft = np.interp(halfVal, ppmdata[leftIdx:leftIdx+2], xvals[leftIdx:leftIdx+2])
    else:
        xLeft = xvals[0]

    rightIdxRel = np.where(ppmdata[peakIdx:] <= halfVal)[0]
    if rightIdxRel.size > 0:
        rightIdx = peakIdx + rightIdxRel[0]
        xRight = np.interp(halfVal, ppmdata[rightIdx-1:rightIdx+1], xvals[rightIdx-1:rightIdx+1])
    else:
        xRight = xvals[-1]

    FWHM_Hz = (xRight - xLeft)
    FWHM_ppm = FWHM_Hz / CF_New * 1e6

    ppm_summary[1, i] = FWHM_Hz
    ppm_summary[2, i] = FWHM_ppm

    # Label
    name = os.path.splitext(os.path.basename(dat_file))[0]
    parts = name.split('_')
    GA_label = parts[-1]
    GA_labels.append(f"GA_{GA_label}")

    titlename = f"FID GA = {GA_label}"

    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(xvals, ppmdata, 'b', lw=1.2)
    plt.plot([xLeft, xRight], [0.5, 0.5], 'k', lw=5)

    plt.xlim([-500, 500])
    plt.ylim([0, 1.05])
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Normalized Amplitude')
    plt.title(titlename)

    plt.text(txtX, 0.85, f'CF = {round(CF_New)} Hz', weight='bold')
    plt.text(txtX, 0.75, f'FWHM = {FWHM_Hz:.2f} Hz', weight='bold')
    plt.text(txtX, 0.65, f'FWHM = {FWHM_ppm:.2f} ppm', weight='bold')

    plt.savefig(os.path.join(plotsdir, f"{name}.jpg"))
    plt.close()

# --- Excel ---
df_summary = pd.DataFrame(ppm_summary, index=['CF', 'FWHM Hz', 'FWHM ppm'], columns=GA_labels)
fft_df = pd.DataFrame(np.column_stack(fft_data_all))
fft_df.insert(0, 'SampleIdx', np.arange(1, fft_df.shape[0]+1))
fft_df.columns = ['SampleIdx'] + GA_labels

xlspath = os.path.join(exceldir, 'PPM_All_GA_Info.xlsx')
with pd.ExcelWriter(xlspath) as writer:
    fft_df.to_excel(writer, sheet_name='PPM_Info_full', index=False)
    df_summary.to_excel(writer, sheet_name='PPM_Summary')

# --- Polar plot ---
angle_deg = [int(lbl.split('_')[1]) for lbl in GA_labels]
angle_deg_sorted, idx = zip(*sorted(zip(angle_deg, range(len(angle_deg)))))
FWHM_ppm_sorted = ppm_summary[2, idx]

theta = np.deg2rad(list(angle_deg_sorted) + [angle_deg_sorted[0]])
r_ppm = list(FWHM_ppm_sorted) + [FWHM_ppm_sorted[0]]
mean_circle = [5] * len(theta)

plt.figure(figsize=(8, 8))
ax = plt.subplot(111, polar=True)
ax.plot(theta, r_ppm, 'k-', lw=1)
ax.plot(theta, mean_circle, 'r-', lw=1)
ax.plot(theta, r_ppm, 'g*', markersize=6)
ax.set_title('HOMOGENEITY v. GA', weight='bold')

ax.set_rmax(10)
ax.set_rticks(range(0, 11, 2))
ax.set_theta_zero_location('E')
ax.set_theta_direction(-1)
ax.set_xticks(np.deg2rad(angle_deg_sorted))

plt.savefig(os.path.join(plotsdir, 'Homogeneity_vs_GA_POLAR_PPM.png'))
plt.close()

print(f"Done. Results saved in {qadir}")
