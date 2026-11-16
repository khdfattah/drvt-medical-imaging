import math
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="DRVT Medical Imaging Engine",
    page_icon="🧠",
    layout="wide"
)

# -------------------------------------------------
# Constants from DRVT Medical Imaging Framework
# -------------------------------------------------

V_RES = 286.398      # nm^3
K = 13.0 / 3.0       # eV/nm^2

st.title("🧠 DRVT Medical Imaging Design Engine")

st.markdown("""
### Medical Imaging Framework, applying Dynamic Resonant Volume Theory (DRVT)by Dr. Khalid Abdel Fattah to resolve classical bottlenecks in Photonic Medical Imaging.
Based on:
- Resonant Volume: 286.398 nm³
- Geometric Energy Coefficient: 13/3 eV/nm²
Application:
- Fluorescence-Guided Surgery
- Microscopy
- Photodynamic Therapy
- Biomedical Imaging
""")

# -------------------------------------------------
# Imaging Parameters
# -------------------------------------------------

st.header("Imaging Configuration")

col1, col2 = st.columns(2)

with col1:

    lambda_exc = st.number_input(
        "Excitation Wavelength (nm)",
        value=405.0
    )

    p_exc_mw = st.number_input(
        "Excitation Power (mW)",
        value=30.0
    )

    eta_f = st.slider(
        "Fluorescence Efficiency ηf",
        0.0,
        1.0,
        0.10
    )

with col2:

    lambda_em = st.number_input(
        "Emission Wavelength (nm)",
        value=635.0
    )

    scan_volume = st.number_input(
        "Interaction Volume Vscan (nm³)",
        value=1e14,
        format="%.2e"
    )

# -------------------------------------------------
# Excitation Calculations
# -------------------------------------------------

A_exc = V_RES / lambda_exc
E_exc = K * A_exc

A_em = V_RES / lambda_em
E_em = K * A_em

E_exc_J = E_exc * 1.602e-19

N_exc = (p_exc_mw * 1e-3) / E_exc_J

vg = 2.14e17

tau_exc = lambda_exc / vg

N_photons = N_exc * tau_exc

# -------------------------------------------------
# DRVT Metrics
# -------------------------------------------------

N_res = scan_volume / V_RES

PCI = N_photons / N_res

CED = PCI * E_exc

FVI = eta_f * (1 - PCI)

# -------------------------------------------------
# Classification
# -------------------------------------------------

if PCI < 1e-10:
    regime = "Ultra-Low Congestion"
elif PCI < 1e-8:
    regime = "Low Congestion"
elif PCI < 1e-6:
    regime = "Moderate Congestion"
elif PCI < 1e-4:
    regime = "High Congestion"
else:
    regime = "Extreme Congestion"

# -------------------------------------------------
# Output
# -------------------------------------------------

st.header("DRVT Imaging Metrics")

m1, m2, m3 = st.columns(3)

m1.metric(
    "Photon Congestion Index (PCI)",
    f"{PCI:.2e}"
)

m2.metric(
    "Congestion Energy Density (CED)",
    f"{CED:.2e}"
)

m3.metric(
    "Fluorescence Visibility Index (FVI)",
    f"{FVI:.4f}"
)

st.info(f"Congestion Regime: {regime}")

# -------------------------------------------------
# Detailed Table
# -------------------------------------------------

df = pd.DataFrame({
    "Parameter": [
        "Excitation Area Aeff",
        "Excitation Energy",
        "Emission Area Aeff",
        "Emission Energy",
        "Photon Flux",
        "Transient Photons",
        "Resonant Capacity",
        "PCI",
        "CED",
        "FVI"
    ],
    "Value": [
        f"{A_exc:.4f} nm²",
        f"{E_exc:.4f} eV",
        f"{A_em:.4f} nm²",
        f"{E_em:.4f} eV",
        f"{N_exc:.3e}",
        f"{N_photons:.3e}",
        f"{N_res:.3e}",
        f"{PCI:.3e}",
        f"{CED:.3e}",
        f"{FVI:.4f}"
    ]
})

st.dataframe(df, use_container_width=True)

# -------------------------------------------------
# Photobleaching Risk
# -------------------------------------------------

st.header("Photobleaching Risk Predictor")

if PCI < 1e-8:
    st.success("Low Photobleaching Risk")
elif PCI < 1e-6:
    st.warning("Moderate Photobleaching Risk")
else:
    st.error("High Photobleaching Risk")

# -------------------------------------------------
# Imaging Recommendation
# -------------------------------------------------

st.header("Engineering Recommendation")

if FVI > 0.7:
    st.success(
        "Excellent imaging conditions with strong fluorescence visibility."
    )
elif FVI > 0.3:
    st.warning(
        "Acceptable imaging conditions but optimization may improve contrast."
    )
else:
    st.error(
        "Poor fluorescence visibility. Reduce congestion or improve fluorophore efficiency."
    )

