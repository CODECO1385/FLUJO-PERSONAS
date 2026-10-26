"""Interfaz Streamlit: carga -> configuración -> análisis -> resultados."""
import os
import shutil
import tempfile

import pandas as pd
import streamlit as st

import analytics as an
import exports as ex
import video_processor as vp
import visualizations as viz
import zones as zn

st.set_page_config(page_title="Flujo de personas", layout="wide")
ss = st.session_state
for k, v in {"tmpdir": None, "path": None, "info": None, "upload_key": None, "result": None,
             "zver": 0, "zones_df": pd.DataFrame({"Zona": [], "Puntos": []})}.items():
    ss.setdefault(k, v)


def cleanup():
    if ss.tmpdir and os.path.isdir(ss.tmpdir):
        shutil.rmtree(ss.tmpdir, ignore_errors=True)


def reset_all():
    cleanup()
    for k in list(ss.keys()):
        del ss[k]
    st.rerun()


def fmt(v, unit="s", nd=1):
    return "No se pudo determinar" if v is None else (f"{v:.{nd}f} {unit}".strip() if isinstance(v, float) else f"{v} {unit}".strip())


def s_(v):
    return "" if pd.isna(v) else str(v)


st.title("Análisis de movimiento y flujo de personas")
st.sidebar.markdown("**Privacidad**\n\nTodo se procesa en este equipo. Los videos se guardan solo temporalmente en:\n\n"
                    f"`{ss.tmpdir or tempfile.gettempdir() + '/flujo_personas_*'}`\n\n"
                    "y se borran al iniciar un análisis nuevo. Los IDs («Persona N») son temporales y no identifican a nadie.")
if st.sidebar.button("🔄 Iniciar análisis nuevo"):
    reset_all()

tab1, tab2, tab3, tab4 = st.tabs(["1. Video", "2. Espacio", "3. Análisis", "4. Resultados"])

# ---------------- 1. Video ----------------
with tab1:
    up = st.file_uploader("Carga un video (MP4, MOV o AVI)", type=["mp4", "mov", "avi"])
    if up is not None and ss.upload_key != (up.name, up.size):
        cleanup()
        ss.tmpdir = tempfile.mkdtemp(prefix="flujo_personas_")
        ss.path = os.path.join(ss.tmpdir, "video" + os.path.splitext(up.name)[1].lower())
        with open(ss.path, "wb") as f:
            f.write(up.getbuffer())
        ss.upload_key, ss.result = (up.name, up.size), None
        try:
            ss.info = vp.probe_video(ss.path)
        except vp.VideoError as e:
            ss.info = None
            st.error(str(e))
    if ss.info:
        i = ss.info
        c = st.columns(4)
        c[0].metric("Duración", f"{i.duration:.1f} s")
        c[1].metric("Resolución", f"{i.width}×{i.height}")
        c[2].metric("FPS", f"{i.fps:.1f}")
        c[3].metric("Fotogramas", i.frame_count)
        if i.duration > 240:
            st.warning("El video es largo (> 4 min). Puede tardar bastante; considera el modo de prueba.")
        if up is not None:
            st.video(up)

# ---------------- 2. Espacio ----------------
cfg = zn.SpaceConfig()
with tab2:
    if not ss.info:
        st.info("Carga un video primero.")
    else:
        i = ss.info
        W, H = i.width, i.height
        t_ref = st.slider("Fotograma de referencia (s)", 0.0, float(i.duration), 0.0, 0.5)
        try:
            ref = vp.read_frame_at(ss.path, t_ref)
        except vp.VideoError as e:
            st.error(str(e)); st.stop()

        with st.expander("Cargar configuración guardada"):
            f = st.file_uploader("Archivo JSON de configuración", type=["json"], key="cfgup")
            if f is not None and st.button("Aplicar configuración"):
                try:
                    c = zn.SpaceConfig.from_json(f.getvalue().decode("utf-8"))
                    if c.line:
                        ss.use_line = True
                        ss.lx1, ss.ly1 = int(c.line.p1[0] * 100), int(c.line.p1[1] * 100)
                        ss.lx2, ss.ly2 = int(c.line.p2[0] * 100), int(c.line.p2[1] * 100)
                        ss.side = "Derecha" if c.line.inside_side == 1 else "Izquierda"
                    ss.zones_df = pd.DataFrame({"Zona": [z.name for z in c.zones],
                                                "Puntos": [zn.points_to_text(z.points) for z in c.zones]})
                    ss.zver += 1
                    w = zn.check_compatibility(c, (W, H))
                    ss.cfg_warning = w
                    st.rerun()
                except Exception as e:
                    st.error(f"Configuración inválida: {e}")
        if ss.get("cfg_warning"):
            st.warning(ss.cfg_warning)

        st.subheader("Línea de entrada/salida")
        use_line = st.checkbox("Usar línea de entrada/salida", value=True, key="use_line")
        c = st.columns(5)
        lx1 = c[0].slider("P1 x %", 0, 100, 10, key="lx1")
        ly1 = c[1].slider("P1 y %", 0, 100, 50, key="ly1")
        lx2 = c[2].slider("P2 x %", 0, 100, 90, key="lx2")
        ly2 = c[3].slider("P2 y %", 0, 100, 50, key="ly2")
        side = c[4].radio("Interior del local a la… (de P1 a P2)", ["Derecha", "Izquierda"], key="side")
        st.caption("La flecha amarilla «interior» indica el lado del local. Cruzar hacia ella = entrada; hacia el otro lado = salida.")

        st.subheader("Zonas de interés")
        with st.expander("Agregar rectángulo rápido"):
            q = st.columns(5)
            qn = q[0].text_input("Nombre", "Mesas")
            qx1, qy1 = q[1].number_input("x1 %", 0, 100, 0), q[2].number_input("y1 %", 0, 100, 0)
            qx2, qy2 = q[3].number_input("x2 %", 0, 100, 50), q[4].number_input("y2 %", 0, 100, 50)
            if st.button("Agregar zona"):
                txt = f"{qx1},{qy1}; {qx2},{qy1}; {qx2},{qy2}; {qx1},{qy2}"
                ss.zones_df = pd.concat([ss.zones_df, pd.DataFrame({"Zona": [qn], "Puntos": [txt]})], ignore_index=True)
                ss.zver += 1
                st.rerun()
       ss.zones_df = ss.zones_df.astype({"Zona": "object", "Puntos": "object"})  
       edited = st.data_editor(ss.zones_df, num_rows="dynamic", use_container_width=True, key=f"zed{ss.zver}",            
                                column_config={"Puntos": st.column_config.TextColumn("Puntos (% x,y; x,y; …)")})
        zlist, errs = [], []
        for _, r in edited.iterrows():
            n, p = s_(r.get("Zona")).strip(), s_(r.get("Puntos")).strip()
            if not n and not p:
                continue
            try:
                zlist.append(zn.Zone(n or "Zona", zn.parse_points(p)))
            except ValueError as e:
                errs.append(f"{n or 'Zona'}: {e}")
        for e in errs:
            st.error(e)
        ss.zones_df = edited.reset_index(drop=True)
        line = zn.EntryLine((lx1 / 100, ly1 / 100), (lx2 / 100, ly2 / 100), 1 if side == "Derecha" else -1) if use_line else None
        cfg = zn.SpaceConfig(line, zlist, (W, H))
        img = ref.copy()
        viz.draw_space_overlay(img, cfg)
        st.image(img[:, :, ::-1], use_container_width=True)
        st.download_button("💾 Guardar configuración (JSON)", cfg.to_json(), "configuracion_espacio.json", "application/json")
        ss.cfg = cfg

# ---------------- 3. Análisis ----------------
with tab3:
    if not ss.info:
        st.info("Carga un video primero.")
    else:
        i = ss.info
        c = st.columns(3)
        model = c[0].selectbox("Modelo YOLO", ["yolov8n.pt", "yolov8s.pt", "yolo11n.pt"],
                               help="El más pequeño (n) es el más rápido. Los pesos se descargan la primera vez.")
        conf = c[1].slider("Umbral de confianza", 0.1, 0.9, 0.35, 0.05)
        fps_t = c[2].select_slider("Fotogramas por segundo a procesar", [1, 2, 3, 5, 10, 15, 30], 5)
        c = st.columns(3)
        width = c[0].selectbox("Resolución de procesamiento (ancho)", [480, 640, 960, 1280, 0], 2,
                               format_func=lambda v: "Original" if v == 0 else f"{v}px")
        test_mode = c[1].checkbox("Modo de prueba (solo los primeros 20 s)")
        write_video = c[2].checkbox("Generar video procesado", True)
        if st.button("▶️ Iniciar análisis", type="primary"):
            try:
                from tracker import PersonTracker
                with st.spinner("Cargando modelo…"):
                    tracker = PersonTracker(model, conf)
            except Exception as e:
                st.error(f"No se pudo cargar el detector: {e}")
                st.stop()
            cfg_use = ss.get("cfg") or zn.SpaceConfig()
            out = os.path.join(ss.tmpdir, "procesado.mp4")
            bar = st.progress(0.0, text="Procesando…")
            settings = vp.ProcSettings(target_fps=float(fps_t), max_width=width,
                                       max_seconds=20 if test_mode else None, write_video=write_video)
            try:
                tracks, pinfo = vp.process_video(ss.path, tracker, settings, cfg_use, out if write_video else None,
                                                 lambda p, m: bar.progress(p, text=m))
            except vp.VideoError as e:
                st.error(str(e)); st.stop()
            bar.progress(1.0, text="Calculando estadísticas…")
            res = an.analyze(tracks, cfg_use, (i.width, i.height), pinfo["segundos_analizados"], pinfo["sample_dt"])
            res.update(pinfo=pinfo, cfg=cfg_use,
                       settings={"modelo": model, "confianza": conf, "fps_procesados": fps_t, "ancho": width, "modo_prueba": test_mode},
                       video=out if (write_video and not pinfo["video_error"] and os.path.exists(out)) else None,
                       ref=vp.read_frame_at(ss.path, 0.0))
            ss.result = res
            bar.empty()
            st.success(f"Análisis terminado en {pinfo['tiempo_procesamiento_s']:.1f} s. Ve a «4. Resultados».")

# ---------------- 4. Resultados ----------------
with tab4:
    R = ss.result
    if not R:
        st.info("Aún no hay resultados.")
    elif R["people"].empty:
        st.warning("No se detectaron personas (o los seguimientos fueron demasiado cortos). Prueba bajar el umbral de confianza o aumentar la resolución.")
    else:
        S, P, E = R["summary"], R["people"], R["events"]
        cols = st.columns(4)
        cols[0].metric("IDs detectados", S["ids_detectados"])
        cols[1].metric("Entradas válidas", fmt(S["entradas_validas"], ""))
        cols[2].metric("Salidas válidas", fmt(S["salidas_validas"], ""))
        cols[3].metric("Zona con más actividad", S["zona_mayor_actividad"] or "Datos insuficientes")
        cols = st.columns(4)
        cols[0].metric("Presentes al inicio", fmt(S["presentes_al_inicio"], ""))
        cols[1].metric("Presentes al final", fmt(S["presentes_al_final"], ""))
        cols[2].metric("Permanencia media / mediana", "Datos insuficientes" if S["permanencia_media_s"] is None
                       else f"{S['permanencia_media_s']:.1f} / {S['permanencia_mediana_s']:.1f} s ({S['registros_completos']} completos)")
        cols[3].metric("Tiempo observado promedio", fmt(S["tiempo_observado_medio_s"]))
        st.caption("«Tiempo observado» = primera a última detección. «Permanencia estimada» = cruce de entrada a cruce de salida del mismo ID. No son lo mismo.")

        st.subheader("Personas observadas en el tiempo")
        st.pyplot(viz.timeline_fig(R["timeline"]))

        st.subheader("Trayectorias")
        ids = sorted(P["id"].tolist())
        sel = st.multiselect("Trayectorias a mostrar", ids, default=ids[:10], format_func=lambda v: f"Persona {v}")
        st.image(viz.trajectories_image(R["ref"], R["tracks"], sel, R["cfg"]), use_container_width=True)

        st.subheader("Mapa de calor")
        mode = st.radio("Basado en", ["posiciones", "tiempo"], horizontal=True,
                        format_func=lambda m: "Concentración de posiciones" if m == "posiciones" else "Tiempo acumulado (s)")
        hm = viz.heatmap_image(R["ref"], R["tracks"], mode, R["max_gap"])
        if hm is not None:
            st.image(hm, use_container_width=True)

        st.subheader("Zonas y flujo")
        if S["tiempo_por_zona_s"]:
            st.dataframe(pd.DataFrame({"Zona": list(S["tiempo_por_zona_s"]), "Tiempo observado (s)": list(S["tiempo_por_zona_s"].values())}),
                         hide_index=True)
        else:
            st.write("Datos insuficientes: no hay zonas configuradas o nadie pasó por ellas.")
        if S["transiciones"]:
            st.pyplot(viz.flow_fig(S["transiciones"]))
            st.dataframe(pd.DataFrame({"Transición": list(S["transiciones"]), "Cantidad": list(S["transiciones"].values())}), hide_index=True)
        else:
            st.write("Transiciones entre zonas: datos insuficientes.")

        st.subheader("Detalle por identificador temporal")
        st.dataframe(P, use_container_width=True, hide_index=True)

        if R["video"]:
            st.subheader("Video procesado")
            st.video(R["video"])
            st.caption("Si no se reproduce en el navegador (códec mp4v), descárgalo y ábrelo con VLC.")
        elif R["pinfo"]["video_error"]:
            st.warning(R["pinfo"]["video_error"])

        st.subheader("Limitaciones y calidad")
        n_low = int((P["calidad"] == "Baja").sum())
        st.markdown(
            f"- Los IDs son temporales; si el rastreador pierde a alguien y lo recupera con otro ID, **no se unen**. "
            f"Posibles cambios de ID detectados: **{len(S['posibles_cambios_id'])}** (ver columna *notas*).\n"
            f"- Registros de calidad baja: **{n_low}** de {len(P)}. Los registros incompletos no representan la permanencia real.\n"
            f"- Se descartaron **{S['ids_descartados_por_ruido']}** seguimientos con muy pocas observaciones (probable ruido).\n"
            f"- Procesado a {R['pinfo']['fps_video'] / R['pinfo']['stride']:.1f} fps efectivos, {R['pinfo']['tamano_procesamiento'][0]}×{R['pinfo']['tamano_procesamiento'][1]} px; "
            f"errores del detector: {R['pinfo']['errores_detector']}.\n"
            "- Posición = centro inferior del cuadro; oclusiones y personas parcialmente visibles reducen la precisión.\n"
            "- Todas las cifras son estimaciones a partir de este video, no mediciones exactas.")

        st.subheader("Descargas")
        d = st.columns(5)
        d[0].download_button("CSV personas", ex.people_csv(P), "personas.csv", "text/csv")
        d[1].download_button("CSV eventos", ex.events_csv(E), "eventos.csv", "text/csv")
        d[2].download_button("JSON resumen", ex.summary_json(S, R["cfg"], R["settings"], R["pinfo"]), "resumen.json", "application/json")
        if R["video"]:
            with open(R["video"], "rb") as f:
                d[3].download_button("Video procesado", f.read(), "video_procesado.mp4", "video/mp4")
        d[4].download_button("Todo (ZIP)", ex.build_zip(P, E, S, R["cfg"], R["settings"], R["pinfo"], R["video"]), "resultados.zip", "application/zip")
        if st.button("🔄 Nuevo análisis"):
            reset_all()
