import io

import ezdxf
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

"""
Streamlit application for calculating and building the profile of a
cycloidal drive with intermediate rolling elements (VPTK).

Enter the main data (gear ratio, ball diameter, rigid wheel profile radius)
and the application will automatically compute all parameters and build:
1) rigid wheel profile (BASE_WHEEL_SHAPE)
2) separator (SEPARATOR)
3) wave generator / eccentric (ECCENTRIC)
4) balls (BALLS)
5) outer diameter of the reducer (OUT_DIAMETER)

The result can be downloaded as a DXF file that opens in any CAD.
"""


def compute_geometry(i, dsh, Rout, D, u, resolution):
    """Compute all parameters and coordinates of the VPTK profile.

    Returns a dict with parameters and coordinate arrays, or raises
    ValueError if the geometry is not feasible.
    """
    e = 0.2 * dsh
    zg = (i + 1) * u
    zsh = i
    Rin = Rout - 2 * e
    rsh = dsh / 2
    rd = Rin + e - dsh
    hc = 2.2 * e
    Rsep_m = rd + rsh
    Rsep_out = Rsep_m + hc / 2
    Rsep_in = Rsep_m - hc / 2

    Rin_min = (1.03 * dsh) / np.sin(np.pi / zg)
    if Rin <= Rin_min:
        raise ValueError(
            "This won't work -_-)\n"
            "The inner radius of the rigid wheel grooves Rin ({0:.3f} mm) must be "
            "greater than {1:.3f} mm. Increase Rout or decrease the gear ratio (i)!".format(
                Rin, Rin_min
            )
        )

    theta = np.linspace(0, 2 * np.pi, resolution)

    S = np.sqrt((rsh + rd) ** 2 - np.power(e * np.sin(zg * theta), 2))
    l = e * np.cos(zg * theta) + S
    Xi = np.arctan2(e * zg * np.sin(zg * theta), S)

    x = l * np.sin(theta) + rsh * np.sin(theta + Xi)
    y = l * np.cos(theta) + rsh * np.cos(theta + Xi)
    xy = np.stack((x, y), axis=1)

    sh_angle = np.linspace(0, 1, zsh + 1) * 2 * np.pi
    S_sh = np.sqrt((rsh + rd) ** 2 - np.power(e * np.sin(zg * sh_angle), 2))
    l_Sh = e * np.cos(zg * sh_angle) + S_sh
    x_sh = l_Sh * np.sin(sh_angle)
    y_sh = l_Sh * np.cos(sh_angle)

    return {
        "e": e,
        "zg": zg,
        "zsh": zsh,
        "Rin": Rin,
        "rsh": rsh,
        "rd": rd,
        "hc": hc,
        "Rsep_m": Rsep_m,
        "Rsep_out": Rsep_out,
        "Rsep_in": Rsep_in,
        "x": x,
        "y": y,
        "xy": xy,
        "x_sh": x_sh,
        "y_sh": y_sh,
    }


def build_dxf(g, D, flags):
    """Create a DXF document and return it as bytes."""
    doc = ezdxf.new("R2000")
    msp = doc.modelspace()

    if flags["base_wheel_shape"]:
        msp.add_point([0, 0])
        msp.add_lwpolyline(g["xy"])

    if flags["separator"]:
        msp.add_circle((0, 0), radius=g["Rsep_out"])
        msp.add_circle((0, 0), radius=g["Rsep_in"])

    if flags["eccentric"]:
        msp.add_point([0, g["e"]])
        msp.add_lwpolyline([[0, 0], [0, g["e"]]])
        msp.add_lwpolyline([[-6, 0], [6, 0]])
        msp.add_lwpolyline([[-3, g["e"]], [3, g["e"]]])
        msp.add_circle((0, g["e"]), radius=g["rd"])

    if flags["balls"]:
        for k in range(g["zsh"]):
            msp.add_circle((g["x_sh"][k], g["y_sh"][k]), radius=g["rsh"])

    if flags["out_diameter"]:
        msp.add_circle((0, 0), radius=D / 2)

    # ezdxf can write to a text stream; collect into a string and encode to bytes
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def build_plot(g, D, flags):
    """Build the profile visualization in matplotlib."""
    fig, ax = plt.subplots(figsize=(8, 8))

    if flags["base_wheel_shape"]:
        ax.plot(g["x"], g["y"], linewidth=1.0, label="Rigid wheel profile")

    if flags["eccentric"]:
        ax.plot([0, 0], (0, g["e"]), ".", linewidth=1.0)
        ax.plot([-6, 6], (0, 0), "--k", linewidth=1.0)
        ax.plot([-3, 3], (g["e"], g["e"]), "--k", linewidth=1.0)
        rd_circle = plt.Circle((0, g["e"]), g["rd"], color="b", fill=False, linewidth=1.0)
        ax.add_patch(rd_circle)

    if flags["out_diameter"]:
        D_circle = plt.Circle((0, 0), D / 2, color="b", fill=False, linewidth=1.0)
        ax.add_patch(D_circle)

    if flags["separator"]:
        Rsep_out_circle = plt.Circle((0, 0), g["Rsep_out"], fill=False, linewidth=1.0)
        Rsep_in_circle = plt.Circle((0, 0), g["Rsep_in"], fill=False, linewidth=1.0)
        ax.add_patch(Rsep_out_circle)
        ax.add_patch(Rsep_in_circle)

    if flags["balls"]:
        for k in range(g["zsh"]):
            sh_circle = plt.Circle(
                (g["x_sh"][k], g["y_sh"][k]), g["rsh"], color="r", fill=False, linewidth=1.0
            )
            ax.add_patch(sh_circle)

    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle=":", linewidth=0.5)
    ax.set_xlabel("X, mm")
    ax.set_ylabel("Y, mm")
    ax.set_title("VPTK profile")
    return fig


# ------------------------------------------------------------------------- #
# Streamlit interface
# ------------------------------------------------------------------------- #
st.set_page_config(page_title="VPTK profile calculator", page_icon="⚙️", layout="wide")

st.title("⚙️ Cycloidal drive profile calculator (VPTK)")
st.caption("Cycloidal drive with intermediate rolling elements.")

with st.sidebar:
    st.header("Input data")
    i = st.number_input("Gear ratio (i)", min_value=2, max_value=200, value=17, step=1)
    dsh = st.number_input(
        "Ball diameter, mm (dsh)", min_value=0.5, max_value=50.0, value=6.0, step=0.5
    )
    Rout = st.number_input(
        "Outer radius of rigid wheel grooves, mm (Rout)",
        min_value=1.0,
        max_value=500.0,
        value=38.0,
        step=1.0,
    )
    D = st.number_input(
        "Outer diameter of the reducer, mm (D)", min_value=1.0, max_value=1000.0, value=90.0, step=1.0
    )
    u = st.number_input(
        "Number of waves (u)",
        min_value=1,
        max_value=1,
        value=1,
        step=1,
        help="DO NOT CHANGE: values greater than 1 have not been verified.",
    )
    resolution = st.slider(
        "Profile resolution (number of points)", min_value=100, max_value=2000, value=600, step=50
    )

    st.header("What to build")
    flags = {
        "base_wheel_shape": st.checkbox("Rigid wheel profile", value=True),
        "separator": st.checkbox("Separator", value=True),
        "eccentric": st.checkbox("Eccentric / wave generator", value=True),
        "balls": st.checkbox(
            "Balls (for demonstration only)",
            value=False,
            help="Not recommended for the drawing: balls are not spaced at equal distances.",
        ),
        "out_diameter": st.checkbox("Outer diameter of the reducer", value=True),
    }

    out_file = st.text_input("DXF file name", value="vptc.dxf")

# Calculation
try:
    g = compute_geometry(int(i), float(dsh), float(Rout), float(D), int(u), int(resolution))
except ValueError as err:
    st.error(str(err))
    st.stop()

col_plot, col_params = st.columns([3, 2])

with col_params:
    st.subheader("Main VPTK parameters")
    st.markdown(
        f"""
| Parameter | Value |
|---|---|
| Gear ratio | {int(i)} |
| Eccentricity | {g['e']:.3f} mm |
| Eccentric radius | {g['rd']:.3f} mm |
| Outer profile radius | {float(Rout):.3f} mm |
| Inner profile radius | {g['Rin']:.3f} mm |
| Number of profile grooves | {g['zg']} |
| Number of balls | {g['zsh']} |
| Ball diameter | {float(dsh):.3f} mm |
| Separator pitch radius | {g['Rsep_m']:.3f} mm |
| Separator thickness | {g['hc']:.3f} mm |
"""
    )

    dxf_bytes = build_dxf(g, float(D), flags)
    st.download_button(
        label="⬇️ Download DXF",
        data=dxf_bytes,
        file_name=out_file if out_file.strip() else "vptc.dxf",
        mime="application/dxf",
    )

with col_plot:
    st.subheader("Profile visualization")
    fig = build_plot(g, float(D), flags)
    st.pyplot(fig)
