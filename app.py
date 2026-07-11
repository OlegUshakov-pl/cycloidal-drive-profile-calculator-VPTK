import io

import ezdxf
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

"""
Streamlit-приложение для расчета и построения профиля волнового редуктора
с промежуточными телами качения (ВПТК).

Вводите основные данные (передаточное число, диаметр шариков, радиус профиля
жесткого колеса), а приложение автоматически посчитает все параметры и построит:
1) профиль жесткого колеса (BASE_WHEEL_SHAPE)
2) сепаратор (SEPARATOR)
3) волнообразователь/эксцентрик (ECCENTRIC)
4) шарики (BALLS)
5) внешний диаметр редуктора (OUT_DIAMETER)

Результат можно скачать в формате DXF, который открывается в любом CAD.
"""


def compute_geometry(i, dsh, Rout, D, u, resolution):
    """Расчет всех параметров и координат профиля ВПТК.

    Возвращает словарь с параметрами и массивами координат, либо бросает
    ValueError, если геометрия невозможна.
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
            "Так не пойдет -_-)\n"
            "Внутренний радиус впадин жесткого колеса Rin ({0:.3f} мм) должен быть "
            "больше {1:.3f} мм. Увеличьте Rout или уменьшите передаточное число (i)!".format(
                Rin, Rin_min
            )
        )

    theta = np.linspace(0, 2 * np.pi, resolution)

    S_arg = (rsh + rd) ** 2 - np.power(e * np.sin(zg * theta), 2)
    S = np.sqrt(np.maximum(S_arg, 0.0))
    l = e * np.cos(zg * theta) + S
    Xi = np.arctan2(e * zg * np.sin(zg * theta), S)

    x = l * np.sin(theta) + rsh * np.sin(theta + Xi)
    y = l * np.cos(theta) + rsh * np.cos(theta + Xi)
    xy = np.stack((x, y), axis=1)

    sh_angle = np.linspace(0, 1, zsh + 1) * 2 * np.pi
    S_sh_arg = (rsh + rd) ** 2 - np.power(e * np.sin(zg * sh_angle), 2)
    S_sh = np.sqrt(np.maximum(S_sh_arg, 0.0))
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
    """Создает DXF-документ и возвращает его как байты."""
    doc = ezdxf.new("R2000")
    msp = doc.modelspace()

    if flags["base_wheel_shape"]:
        msp.add_point([0, 0])
        msp.add_lwpolyline(g["xy"])

    if flags["separator"]:
        msp.add_circle((0, 0), radius=g["Rsep_out"])
        msp.add_circle((0, 0), radius=g["Rsep_in"])

    if flags["eccentric"]:
        half = g["rd"] * 0.8
        msp.add_point([0, g["e"]])
        msp.add_lwpolyline([[0, 0], [0, g["e"]]])
        msp.add_lwpolyline([[-half, 0], [half, 0]])
        msp.add_lwpolyline([[-half / 2, g["e"]], [half / 2, g["e"]]])
        msp.add_circle((0, g["e"]), radius=g["rd"])

    if flags["balls"]:
        for k in range(g["zsh"]):
            msp.add_circle((g["x_sh"][k], g["y_sh"][k]), radius=g["rsh"])

    if flags["out_diameter"]:
        msp.add_circle((0, 0), radius=D / 2)

    # ezdxf умеет писать в текстовый поток; собираем в строку и кодируем в байты
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def build_plot(g, D, flags):
    """Строит визуализацию профиля в matplotlib."""
    fig, ax = plt.subplots(figsize=(8, 8))

    if flags["base_wheel_shape"]:
        ax.plot(g["x"], g["y"], linewidth=1.0, label="Профиль жесткого колеса")

    if flags["eccentric"]:
        half = g["rd"] * 0.8
        ax.plot([0, 0], [0, g["e"]], ".", linewidth=1.0)
        ax.plot([-half, half], [0, 0], "--k", linewidth=1.0)
        ax.plot([-half / 2, half / 2], [g["e"], g["e"]], "--k", linewidth=1.0)
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
    ax.set_xlabel("X, мм")
    ax.set_ylabel("Y, мм")
    ax.set_title("Профиль ВПТК")
    plt.close(fig)
    return fig


# ------------------------------------------------------------------------- #
# Интерфейс Streamlit
# ------------------------------------------------------------------------- #
st.set_page_config(page_title="Расчет профиля ВПТК", page_icon="⚙️", layout="wide")

st.title("⚙️ Расчет профиля волнового редуктора (ВПТК)")
st.caption("Волновой редуктор с промежуточными телами качения.")

with st.sidebar:
    st.header("Исходные данные")
    i = st.number_input("Передаточное число (i)", min_value=2, max_value=200, value=17, step=1)
    dsh = st.number_input(
        "Диаметр шариков, мм (dsh)", min_value=0.5, max_value=50.0, value=6.0, step=0.5
    )
    Rout = st.number_input(
        "Внешний радиус впадин жесткого колеса, мм (Rout)",
        min_value=1.0,
        max_value=500.0,
        value=38.0,
        step=1.0,
    )
    D = st.number_input(
        "Внешний диаметр редуктора, мм (D)", min_value=1.0, max_value=1000.0, value=90.0, step=1.0
    )
    u = st.number_input(
        "Число волн (u)",
        min_value=1,
        max_value=1,
        value=1,
        step=1,
        help="НЕ ТРОГАТЬ: для значений больше 1 расчет не проверялся.",
    )
    resolution = st.slider(
        "Разрешение профиля (кол-во точек)", min_value=100, max_value=2000, value=600, step=50
    )

    st.header("Что строить")
    flags = {
        "base_wheel_shape": st.checkbox("Профиль жесткого колеса", value=True),
        "separator": st.checkbox("Сепаратор", value=True),
        "eccentric": st.checkbox("Эксцентрик / волнообразователь", value=True),
        "balls": st.checkbox(
            "Шарики (только для демонстрации)",
            value=False,
            help="В чертеж переносить не рекомендуется: шарики расположены не на равном расстоянии.",
        ),
        "out_diameter": st.checkbox("Внешний диаметр редуктора", value=True),
    }

    out_file = st.text_input("Имя DXF-файла", value="vptk.dxf")

# Расчет
try:
    g = compute_geometry(int(i), float(dsh), float(Rout), float(D), int(u), int(resolution))
except ValueError as err:
    st.error(str(err))
    st.stop()

col_plot, col_params = st.columns([3, 2])

with col_params:
    st.subheader("Основные параметры ВПТК")
    st.markdown(
        f"""
| Параметр | Значение |
|---|---|
| Передаточное число | {int(i)} |
| Эксцентриситет | {g['e']:.3f} мм |
| Радиус эксцентрика | {g['rd']:.3f} мм |
| Внешний радиус профиля | {float(Rout):.3f} мм |
| Внутренний радиус профиля | {g['Rin']:.3f} мм |
| Число впадин профиля | {g['zg']} |
| Число шариков | {g['zsh']} |
| Диаметр шариков | {float(dsh):.3f} мм |
| Делительный радиус сепаратора | {g['Rsep_m']:.3f} мм |
| Толщина сепаратора | {g['hc']:.3f} мм |
"""
    )

    dxf_bytes = build_dxf(g, float(D), flags)
    st.download_button(
        label="⬇️ Скачать DXF",
        data=dxf_bytes,
        file_name=out_file if out_file.strip() else "vptk.dxf",
        mime="application/dxf",
    )

with col_plot:
    st.subheader("Визуализация профиля")
    fig = build_plot(g, float(D), flags)
    st.pyplot(fig)
