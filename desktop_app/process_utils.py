# process_utils.py

import os
import numpy as np
import matplotlib.pyplot as plt
from twixtools.map_twix import map_twix

def process_dat_file(dat_file, plotsdir):
    twix       = map_twix(dat_file)
    dwelltime  = float(twix[0]['hdr']['MeasYaps']['sRXSPEC']['alDwellTime'][0])
    CF0        = float(twix[0]['hdr']['Dicom']['lFrequency'])
    im         = np.squeeze(np.asarray(twix[0]['image'][:]))

    if im.ndim < 2:
        print(f"❌ Not enough usable image data → {os.path.basename(dat_file)}")
        return None, None, None

    if im.shape[-2] == 2:
        coils     = int(np.prod(im.shape[:-2]))
        _, i_q, nfreq = im.shape
        im_resh   = im.reshape((coils, i_q, nfreq))
        ppmksp    = im_resh[:,0,:] + 1j*im_resh[:,1,:]
    else:
        print(f"❌ Unexpected shape {im.shape}")
        return None, None, None

    ppmfft  = np.abs(np.fft.fftshift(np.fft.ifft(ppmksp, axis=1), axes=1))
    ppmdata = np.sqrt((ppmfft**2).sum(axis=0))
    ppmdata /= ppmdata.max()

    N        = ppmdata.size
    bw_per_px = 1e9 / (dwelltime * N)
    SW       = bw_per_px * N
    xvals    = np.linspace(-SW/2, SW/2, N)

    peakIdx = int(np.argmax(ppmdata))
    peakVal = ppmdata[peakIdx]
    halfVal = peakVal / 2

    delta_cf = round((peakIdx - (N/2)) * bw_per_px)
    CF_new   = CF0 + delta_cf

    xpL, fpL = ppmdata[:peakIdx+1], xvals[:peakIdx+1]
    xLeft     = np.interp(halfVal, xpL, fpL)
    xpR, fpR  = ppmdata[peakIdx:], xvals[peakIdx:]
    xRight   = np.interp(halfVal, xpR[::-1], fpR[::-1])

    FWHM_Hz  = xRight - xLeft
    FWHM_ppm = FWHM_Hz / CF_new * 1e6

    base     = os.path.basename(dat_file)
    GA_label = base.split("_")[-1].replace(".dat","")
    title    = f"FID GA = {GA_label}"

    # ─── Plot spectrum ───────────────────────────────────────
    plt.figure(figsize=(12,6))
    plt.plot(xvals, ppmdata, 'b', linewidth=1.2)
    plt.hlines(halfVal, xLeft, xRight, colors='k', linewidth=5)
    plt.xlim(-500, 500)
    plt.ylim(0, 1.05)
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Normalized Amplitude")
    plt.title(title, fontsize=14, fontweight='bold')

    txtX = 140
    plt.text(txtX, 0.85, f"CF   = {CF_new:.0f} Hz",  fontweight='bold')
    plt.text(txtX, 0.75, f"FWHM = {FWHM_Hz:.2f} Hz", fontweight='bold')
    plt.text(txtX, 0.65, f"FWHM = {FWHM_ppm:.2f} ppm",fontweight='bold')
    plt.text(txtX, 0.35, "GO$_x$ = uT/m or DAQ")
    plt.text(txtX, 0.25, "GO$_y$ = uT/m or DAQ")
    plt.text(txtX, 0.15, "GO$_z$ = uT/m or DAQ")

    plt.grid(True)
    # SAVE AS JPG, dpi=150, tight
    out_path = os.path.join(plotsdir, f"{base}.jpg")
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()

    return [CF_new, FWHM_Hz, FWHM_ppm], ppmdata, GA_label
