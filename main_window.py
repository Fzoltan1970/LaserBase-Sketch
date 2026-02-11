from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QApplication,
    QGroupBox,
    QComboBox,
    QScrollArea,
    QSizePolicy,
    QMessageBox,
    QDialog,
    QRadioButton,
)
from PyQt6.QtGui import QPixmap, QAction, QImage
from PyQt6.QtCore import Qt, QTimer
import sys
import cv2
import numpy as np
import webbrowser
import lang

from image_processor import ImageProcessor
from edit.manager import EditManager
from edit.overlay import EditOverlay
from edit.clean import CleanTool
from edit.simplify import SimplifyTool
from edit.history import History
from model_manager import ModelManager
from styles.default import DefaultStyle
from styles.portrait import PortraitStyle
from styles.architecture import ArchitectureStyle
from styles.vehicle import VehicleStyle
from styles.engrave import EngraveStyle
from vectorizer import Vectorizer
from lang import tr

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # fordítható widget registry
        self._tr = []

        # aktuális rajz mód (egyetlen forrás)
        self.draw_mode = "soft"

        self.setWindowTitle(tr("APP_TITLE"))
        self.resize(1100, 700)

        self.model_manager = ModelManager()
        self.processor = ImageProcessor(self.model_manager)
        self.processor.style = DefaultStyle(self.processor)

        self.cv_image = None        
        self.sketch_image = None
        self.base_sketch = None
        
        # ---- FONTOS: nincs alap mód ----
        self.last_mode = None
        self.last_remove_bg = False
        self.has_generated = False

        # ---------------- EDIT SYSTEM ----------------
        self.edit = EditManager()
        self.overlay = EditOverlay(self.edit)
        self.clean_tool = CleanTool()
        self.simplify_tool = SimplifyTool()
        self.history = History(20)
        self.current_line_layer = None
        self.edit_mode = False
        self.vectorizer = Vectorizer()

        # ---- PREVIEW TIMER ----
        self.preview_timer = QTimer()
        self.preview_timer.setInterval(350)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.auto_preview)

        self.menuBar().hide()
        self._create_topbar()
        self._create_layout()

        self.retranslate_ui()

        self.zoom = 1.0
        self.zoom_min = 0.25
        self.zoom_max = 6.0
      
        QTimer.singleShot(0, self._update_vectorizer_params)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.center_on_screen)

    def center_on_screen(self):
        screen = self.screen().availableGeometry()
        geo = self.frameGeometry()
        geo.moveCenter(screen.center())
        self.move(geo.topLeft())

    # ---------------- TOP BUTTON BAR ----------------
    def _create_topbar(self):

        toolbar = self.addToolBar("main")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

        self.btn_open = QPushButton()
        self.btn_save = QPushButton()
        self.btn_exit = QPushButton()
        self.btn_lang = QPushButton("HU/EN")
        self.btn_about = QPushButton()
        
        for b in (self.btn_open, self.btn_save, self.btn_exit, self.btn_lang, self.btn_about):
            b.setMinimumHeight(28)
            toolbar.addWidget(b)

        toolbar.addSeparator()

        self.btn_open.clicked.connect(self.open_image)
        self.btn_save.clicked.connect(self.save_image)
        self.btn_exit.clicked.connect(self.close)
        self.btn_lang.clicked.connect(self.choose_language)
        self.btn_about.clicked.connect(self.show_about)


    # ---------------- LAYOUT ----------------
    def _create_layout(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        
        # PREVIEW
        self.image_label = QLabel(tr("OPEN_HINT"))
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("color: white;")
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # induláskor töltse ki a nézőablakot
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Expanding)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.image_label)
        self.scroll.setWidgetResizable(True)   # fontos: üres állapothoz
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # valódi háttér
        self.scroll.setStyleSheet("QScrollArea { background: #2b2b2b; border: none; }")
        self.scroll.viewport().setStyleSheet("background: #2b2b2b;")

        main_layout.addWidget(self.scroll, 3)

        # mouse events for edit
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.image_mouse_press
        self.image_label.mouseMoveEvent = self.image_mouse_move
        self.image_label.mouseReleaseEvent = self.image_mouse_release
        self.image_label.wheelEvent = self.image_wheel

        # CONTROL PANEL
        control_panel = QVBoxLayout()

        # -------- GENERATE --------
        # --- AI Model selector ---
        self.model_label = QLabel(tr("MODEL"))
        self.model_combo = QComboBox()

        self.model_combo.addItem("Nincs")

        for name in self.model_manager.registry.keys():
            self.model_combo.addItem(name)
        self.model_combo.setEnabled(True)

        # alapértelmezett
        self.model_combo.setCurrentIndex(0)

        # esemény
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)

        self.group_generate = QGroupBox()
        preset_box = self.group_generate
        preset_layout = QVBoxLayout()

        self.btn_soft = QPushButton(tr("MODE_SOFT"))
        self.btn_strong = QPushButton(tr("MODE_STRONG"))

        # --- új rajz módok (régi presetek) ---
        self.mode_buttons = {}

        def add_mode(name, label):
            btn = QPushButton(label)
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked, n=name: self.set_draw_mode(n))
            preset_layout.addWidget(btn)
            self.mode_buttons[name] = btn

        preset_layout.addWidget(self.model_label)
        preset_layout.addWidget(self.model_combo)

        preset_layout.addWidget(self.btn_soft)
        preset_layout.addWidget(self.btn_strong)

        add_mode("portrait", tr("MODE_PORTRAIT"))
        add_mode("architecture", tr("MODE_ARCHITECTURE"))
        add_mode("vehicle", tr("MODE_VEHICLE"))
        add_mode("engrave", tr("MODE_ENGRAVE"))
              
        preset_box.setLayout(preset_layout)
        control_panel.addWidget(preset_box)

        # layout-ba

        # Generate sliders
        self.group_settings = QGroupBox()
        gen_box = self.group_settings
        gen_layout = QVBoxLayout()

        detail_layout, self.detail_slider = self._make_slider("DETAIL", self.schedule_preview, 100)
        line_layout, self.line_slider = self._make_slider("LINE_THICKNESS", self.schedule_preview, 100)
        bg_layout, self.bg_slider = self._make_slider("BG_CLEAN", self.schedule_preview, 0)

        gen_layout.addLayout(detail_layout)
        gen_layout.addLayout(line_layout)
        gen_layout.addLayout(bg_layout)

        self.detail_slider.setValue(100)       

        gen_box.setLayout(gen_layout)
        control_panel.addWidget(gen_box)

        # -------- STYLE --------
        self.group_style = QGroupBox()
        style_box = self.group_style
        style_layout = QVBoxLayout()

        ink_layout, self.ink_slider = self._make_slider("ILLUSTRATION", self.apply_style, 0)
        comic_layout, self.comic_slider = self._make_slider("COMIC", self.apply_style, 0)
        logo_layout, self.logo_slider = self._make_slider("LOGO", self.apply_style, 0)
        minimal_layout, self.minimal_slider = self._make_slider("MINIMAL", self.apply_style, 0)

        style_layout.addLayout(ink_layout)
        style_layout.addLayout(comic_layout)
        style_layout.addLayout(logo_layout)
        style_layout.addLayout(minimal_layout)

        style_box.setLayout(style_layout)
        control_panel.addWidget(style_box)

        control_panel.addWidget(self._create_edit_panel())
        control_panel.addWidget(self._create_reconstruct_panel())

        control_panel.addStretch()
        main_layout.addLayout(control_panel, 1)       

        # BUTTON CONNECTIONS
        self.btn_soft.clicked.connect(self.set_soft_mode)
        self.btn_strong.clicked.connect(self.set_strong_mode)        

        # ---- EDIT BUTTON CONNECTIONS ----
        self.edit_buttons["brush"].clicked.connect(self._edit_brush)
        self.edit_buttons["clean"].clicked.connect(self._edit_clean)
        self.edit_buttons["simplify"].clicked.connect(self._edit_simplify)

        # induló vizuális állapot
        self.update_mode_buttons()

    def choose_language(self):

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("LANGUAGE"))

        layout = QVBoxLayout(dlg)

        rb_hu = QRadioButton(tr("HUNGARIAN"))
        rb_en = QRadioButton(tr("ENGLISH"))

        # aktuális nyelv
        if lang.LANG == "hu":
            rb_hu.setChecked(True)
        else:
            rb_en.setChecked(True)

        layout.addWidget(rb_hu)
        layout.addWidget(rb_en)

        ok = QPushButton(tr("OK"))
        layout.addWidget(ok)

        def apply():
            lang.set_language("hu" if rb_hu.isChecked() else "en")
            self.retranslate_ui()
            dlg.accept()

        ok.clicked.connect(apply)

        dlg.exec()

    def tr_widget(self, widget, key, setter="setText"):
        self._tr.append((widget, key, setter))
        getattr(widget, setter)(tr(key))

    def retranslate_ui(self):
        self.setWindowTitle(tr("APP_TITLE"))

        self.image_label.setText(tr("OPEN_HINT"))

        self.btn_open.setText(tr("LOAD_IMAGE"))
        self.btn_save.setText(tr("SAVE_IMAGE"))
        self.btn_exit.setText(tr("EXIT"))
        self.btn_about.setText(tr("ABOUT"))

        self.model_label.setText(tr("MODEL"))

        self.group_generate.setTitle(tr("GENERATE"))
        self.group_settings.setTitle(tr("SETTINGS"))
        self.group_style.setTitle(tr("STYLE"))
        self.group_edit.setTitle(tr("EDIT"))
        self.group_vector.setTitle(tr("VECTOR"))

        self.edit_buttons["brush"].setText(tr("ERASER"))
        self.edit_buttons["clean"].setText(tr("DENOISE"))
        self.edit_buttons["simplify"].setText(tr("SIMPLIFY"))

        # --- DRAW MODE BUTTONS ---
        self.btn_soft.setText(tr("MODE_SOFT"))
        self.btn_strong.setText(tr("MODE_STRONG"))

        self.mode_buttons["portrait"].setText(tr("MODE_PORTRAIT"))
        self.mode_buttons["architecture"].setText(tr("MODE_ARCHITECTURE"))
        self.mode_buttons["vehicle"].setText(tr("MODE_VEHICLE"))
        self.mode_buttons["engrave"].setText(tr("MODE_ENGRAVE"))

        # --- MODEL COMBO FIRST ITEM ---
        self.model_combo.setItemText(0, tr("NONE"))

        # --- VECTOR PANEL BUTTONS ---
        self.btn_reconstruct.setText(tr("RECONSTRUCT"))
        self.btn_illustration.setText(tr("ILLUSTRATION_MODE"))

        for w, key, setter in self._tr:
            getattr(w, setter)(tr(key))
    def show_about(self):

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("ABOUT"))

        msg.setText(tr("ABOUT_HTML"))

        msg.setInformativeText(
            f'<a href="https://paypal.me/ZoltanFitos?locale.x=hu_HU&country.x=HU">{tr("ABOUT_LINK")}</a>'
        )

        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)

        msg.exec()
     
    # --------------------------------------------------
    # DRAW MODE CHANGE
    # --------------------------------------------------
    def set_draw_mode(self, mode_name):
        self.draw_mode = mode_name

        # melyik algoritmus
        style_map = {
            "soft": DefaultStyle,
            "strong": DefaultStyle,
            "portrait": PortraitStyle,
            "architecture": ArchitectureStyle,
            "vehicle": VehicleStyle,
            "engrave": EngraveStyle,
        }

        self.processor.style = style_map[mode_name](self.processor)

        # melyik blending mód
        blend = "strong" if mode_name == "strong" else "soft"

        self.update_mode_buttons()
        self.run_processing(False, blend)

    # --------------------------------------------------------
    # PRESETS PANEL
    # --------------------------------------------------------
    def _create_edit_panel(self):

        self.group_edit = QGroupBox()
        box = self.group_edit
        layout = QVBoxLayout(box)

        self.edit_buttons = {}
        edit_tools = {
            "brush": "ERASER",
            "clean": "DENOISE",
            "simplify": "SIMPLIFY",
        }

        for tool, label in edit_tools.items():
            btn = QPushButton(tr(label))

            # --- CSAK A RADÍR MARAD BERAGADÓ GOMB ---
            if tool == "brush":
                btn.setCheckable(True)
            else:
                btn.setCheckable(False)

            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding,
                          QSizePolicy.Policy.Fixed)

            layout.addWidget(btn)
            self.edit_buttons[tool] = btn

        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(6)

        return box

    #
    #Vektor panel
    #
    def _create_reconstruct_panel(self):
        self.group_vector = QGroupBox()
        box = self.group_vector
        layout = QVBoxLayout()

        # ---------- SLIDEREK ----------
        self.vec_detail = QSlider(Qt.Orientation.Horizontal)
        self.vec_detail.setRange(0,100)
        self.vec_detail.setValue(0)
        self.vec_detail.valueChanged.connect(self._update_vectorizer_params)
        lbl = QLabel(); self.tr_widget(lbl,"DETAIL"); layout.addWidget(lbl)
        layout.addWidget(self.vec_detail)

        self.vec_merge = QSlider(Qt.Orientation.Horizontal)
        self.vec_merge.setRange(0,100)
        self.vec_merge.setValue(0)
        self.vec_merge.valueChanged.connect(self._update_vectorizer_params)
        lbl = QLabel(); self.tr_widget(lbl, "CONTINUITY"); layout.addWidget(lbl)
        layout.addWidget(self.vec_merge)

        self.vec_smooth = QSlider(Qt.Orientation.Horizontal)
        self.vec_smooth.setRange(0,100)
        self.vec_smooth.setValue(0)
        self.vec_smooth.valueChanged.connect(self._update_vectorizer_params)
        lbl = QLabel(); self.tr_widget(lbl, "SMOOTHNESS"); layout.addWidget(lbl)
        layout.addWidget(self.vec_smooth)

        # Újrarajzolás
        self.btn_reconstruct = QPushButton(tr("RECONSTRUCT"))
        self.btn_reconstruct.setMinimumHeight(32)
        self.btn_reconstruct.clicked.connect(self._reconstruct_lines)
        layout.addWidget(self.btn_reconstruct)

        # Illusztráció mód
        self.btn_illustration = QPushButton(tr("ILLUSTRATION_MODE"))
        self.btn_illustration.setMinimumHeight(36)
        self.btn_illustration.clicked.connect(self.run_illustration_mode)
        layout.addWidget(self.btn_illustration)

        box.setLayout(layout)
        return box

    # --------------------------------------------------
    # EDIT HANDLERS
    # --------------------------------------------------
    def _disable_all_edit_buttons(self):
        for btn in self.edit_buttons.values():
            btn.setChecked(False)

    def _edit_brush(self, checked):
        self._disable_all_edit_buttons()
        if checked:
            self.edit.enable(True)
            self.edit.set_tool(self.edit.TOOL_BRUSH)
            self.edit_buttons["brush"].setChecked(True)
            self.render_with_edit()
        else:
            self.edit.enable(False)
            self.render_with_edit()

    def _edit_clean(self):
        if self.sketch_image is None:
            return
        self._push_history()
        base = self.edit.apply_to(self.sketch_image)
        self.sketch_image = self.clean_tool.apply(base)
        self.last_line = self.processor.line_sketch(self.sketch_image, 50, 50)
        edges = cv2.Canny(self.sketch_image, 40, 120)
        self.last_line = edges
        self.render_with_edit()

    def _edit_simplify(self):
        if self.sketch_image is None:
            return
        self._push_history()
        base = self.edit.apply_to(self.sketch_image)
        self.sketch_image = self.simplify_tool.apply(base)
        self.last_line = self.processor.line_sketch(self.sketch_image, 50, 50)
        self.last_line = (self.sketch_image < 250).astype("uint8") * 25
        self.render_with_edit()

    def run_illustration_mode(self):
        """Automatikus több lépéses rajz finomítás"""

        if self.sketch_image is None:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.setEnabled(False)
        QApplication.processEvents()

        try:
            # 1. egyszerűsítés
            self._edit_simplify()
            QApplication.processEvents()
 
            # 2. újrarajzolás
            self._reconstruct_lines()
            QApplication.processEvents()

            # 3. tisztítás
            self._edit_clean()
            QApplication.processEvents()

            # 4. végső újrarajzolás
            self._reconstruct_lines()
            QApplication.processEvents()

        finally:
            self.setEnabled(True)
            QApplication.restoreOverrideCursor()


    # ---- ÚJ: VONAL REKONSTRUKCIÓ ----
    def _reconstruct_lines(self):
        if self.sketch_image is None:
            return

        self._push_history()

        paths = self.vectorizer.vectorize(
            self.sketch_image,
            detail=self.vec_detail.value(),
            smooth=self.vec_smooth.value(),
            merge=self.vec_merge.value()
        )

        preview = self.vectorizer.draw_preview(self.sketch_image.shape, paths)
        gray = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)

        # új rajz
        self.sketch_image = gray
        self.base_sketch = gray.copy()

        # edit rendszer frissítés (KRITIKUS)
        self.edit.set_base_image(self.sketch_image)

        # új line layer
        self.last_line = (gray < 250).astype("uint8") * 255
        self.current_line_layer = self.last_line

        self.render_with_edit()

    def set_soft_mode(self):
        self.set_draw_mode("soft")

    def set_strong_mode(self):
        self.set_draw_mode("strong")

    # --------------------------------------------------
    # MODE BUTTON VISUAL STATE
    # --------------------------------------------------
    def update_mode_buttons(self):
        active = "background-color: #c8f7c5;"  # halvány almazöld
        normal = ""

        # minden mód reset
        self.btn_soft.setStyleSheet(normal)
        self.btn_strong.setStyleSheet(normal)

        for btn in getattr(self, "mode_buttons", {}).values():
            btn.setStyleSheet(normal)

        # aktuális mód kiemelése
        if self.draw_mode == "soft":
            self.btn_soft.setStyleSheet(active)
        elif self.draw_mode == "strong":
            self.btn_strong.setStyleSheet(active)
        elif self.draw_mode in self.mode_buttons:
            self.mode_buttons[self.draw_mode].setStyleSheet(active)

    def on_model_changed(self, index):
        if index == 0:
            self.processor.active_model = None
        else:
            if self.processor.models is None:
                return
            name = list(self.processor.models.registry.keys())[index - 1]
            self.processor.active_model = name

        if self.has_generated:
            blend = "strong" if self.draw_mode == "strong" else "soft"
            self.run_processing(False, blend)

    # ---------------- SLIDER ----------------
    def _make_slider(self, key, callback, default=50):
        layout = QHBoxLayout()

        label = QLabel()
        self.tr_widget(label, key)

        slider = QSlider(Qt.Orientation.Horizontal)

        slider.setRange(0, 100)
        slider.setValue(default)
        slider.valueChanged.connect(callback)

        layout.addWidget(label)
        layout.addWidget(slider)

        return layout, slider

    # ---------------- GENERATE ----------------
    def schedule_preview(self):
        if self.cv_image is None:
            return

        # NINCS még generálás → nem rajzol
        if not self.has_generated:
            return

        self.preview_timer.start()

    def auto_preview(self):
        if not self.has_generated:
            return
        # újrarajzolás a jelenlegi móddal
        blend = "strong" if self.draw_mode == "strong" else "soft"
        self.run_processing(False, blend)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr("OPEN_IMAGE_TITLE"), "", "Images (*.png *.jpg *.jpeg *.bmp)")

        # vissza vászon módba új kép előtt
        self.scroll.setWidgetResizable(True)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Expanding)
        self.image_label.setText(tr("OPEN_HINT"))

        if file_path:
            try:
                data = np.fromfile(file_path, dtype=np.uint8)
                self.cv_image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            except Exception:
                self.cv_image = None

            if self.cv_image is None:
                QMessageBox.warning(self, tr("ERROR"), tr("ERROR_LOAD"))
                return

            # átadjuk a feldolgozónak
            self.processor.set_image(self.cv_image)

            self.has_generated = False
            self.last_mode = None

            # kezdő zoom azonnal (mielőtt bármi render történik)
            h, w = self.cv_image.shape[:2]
            self.zoom = self.fit_to_view(w, h)

            # első automatikus rajz
            self.set_draw_mode("soft")

    def run_processing(self, remove_bg=False, mode="soft"):
        if self.cv_image is None:
            return
        
        self.has_generated = True
        self.last_remove_bg = remove_bg
        self.last_mode = mode

        # slider értékek
        detail = 100 - self.detail_slider.value()
        strength = 100 - self.line_slider.value()
        clean = self.bg_slider.value()

        self.base_sketch = self.processor.process(
            mode=mode, detail=detail, strength=strength, clean=clean
        )
        
        self.sketch_image = self.base_sketch.copy()

        # kontúr réteg az edit rendszernek
        self.last_line = self.processor.last_line
       
        # !!! FONTOS: új vászon azonnal
        self.edit.set_base_image(self.sketch_image)
        self.current_line_layer = self.processor.last_line

        self.apply_style()

        self.render_with_edit()

    # ---------------- STYLE ----------------
    def apply_style(self):
        if self.sketch_image is None:
            return

        if self.base_sketch is None:
            return

        img = self.base_sketch.copy()

        ink = self.ink_slider.value()
        comic = self.comic_slider.value()
        logo = self.logo_slider.value()
        minimal = self.minimal_slider.value()

        if ink > 0:
            alpha = 1 + ink / 40
            img = cv2.convertScaleAbs(img, alpha=alpha, beta=-ink)

        if comic > 0:
            k = 1 + comic // 20
            kernel = np.ones((k, k), np.uint8)
            img = cv2.dilate(img, kernel, 1)

        if logo > 0:
            _, img = cv2.threshold(img, 180 - logo, 255, cv2.THRESH_BINARY)

        if minimal > 0:
            k = 1 + minimal // 25
            kernel = np.ones((k, k), np.uint8)
            img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

        self.sketch_image = img
        self.render_with_edit()

    def render_with_edit(self):
        if self.sketch_image is None:
            return

        # biztos azonos méret
        if self.edit.mask is not None and self.edit.mask.shape != self.sketch_image.shape[:2]:
            self.edit.set_base_image(self.sketch_image)

        img = self.edit.apply_to(self.sketch_image)

        if self.edit.enabled:
            img = self.overlay.render(img, self.last_line)

        self.update_preview(img)

    # ---------------- DISPLAY ----------------
    def update_preview(self, img):
        if img is None:
            return

        if len(img.shape) == 2:
            h, w = img.shape
            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)

        pixmap = QPixmap.fromImage(qimg)

        scaled = pixmap.scaled(
            int(w * self.zoom),
            int(h * self.zoom),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())

        # kép megjelenítésekor viewer mód
        self.scroll.setWidgetResizable(False)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Fixed,
                                       QSizePolicy.Policy.Fixed)

    # ---------------- SAVE ----------------
    def save_image(self):
        if self.sketch_image is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, tr("SAVE_IMAGE_TITLE"), "", "PNG Files (*.png)")
        if not file_path:
            return

        # --- Unicode kompatibilis mentés ---
        ext = ".png"
        success, encoded = cv2.imencode(ext, self.sketch_image)

        if success:
            encoded.tofile(file_path)

    # --------------------------------------------------
    # EDIT: coordinate conversion
    # --------------------------------------------------
    def label_to_image(self, event):
        if self.sketch_image is None:
            return None

        # pozíció a labelen belül
        lx = event.position().x()
        ly = event.position().y()

        # scroll offset hozzáadása
        hbar = self.scroll.horizontalScrollBar().value()
        vbar = self.scroll.verticalScrollBar().value()

        lx += hbar
        ly += vbar

        # visszaskálázás képre
        ix = lx / self.zoom
        iy = ly / self.zoom

        img_h, img_w = self.sketch_image.shape[:2]

        if ix < 0 or iy < 0 or ix >= img_w or iy >= img_h:
            return None

        return int(ix), int(iy)

    # --------------------------------------------------
    # EDIT: mouse handling
    # --------------------------------------------------
    def image_mouse_press(self, event):
        if not self.edit.enabled:
            return

        pos = self.label_to_image(event)
        if pos:
            x, y = pos
            self._push_history()
            self.edit.begin_stroke()
            self.edit.apply_at(x, y, self.last_line)
            self.overlay.set_cursor(x, y)
            self.render_with_edit()

    def image_mouse_move(self, event):
        pos = self.label_to_image(event)
        if pos:
            x, y = pos
            self.overlay.set_cursor(x, y)

            if event.buttons():
                self.edit.apply_at(x, y, self.last_line)
                self.render_with_edit()

    def image_mouse_release(self, event):
        self.overlay.clear_cursor()
        if self.edit.enabled:
            
            self.sketch_image = self.edit.apply_to(self.sketch_image)
        self.overlay.clear_cursor()
        self.render_with_edit()

    def image_wheel(self, event):
        delta = event.angleDelta().y()

        # CTRL = zoom
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.1 if delta > 0 else 0.9
            self.zoom = max(self.zoom_min, min(self.zoom_max, self.zoom * factor))
            self.render_with_edit()
            return

        # normál görgő = ecset méret
        size = self.edit.brush.size + (1 if delta > 0 else -1)
        self.edit.brush.set_size(size)
        self.render_with_edit()

    # --------------------------------------------------
    # HISTORY SAVE
    # --------------------------------------------------
    def _push_history(self):
        if self.sketch_image is None:
            return
        self.history.push(self.sketch_image.copy())

    # --------------------------------------------------
    # GLOBAL UNDO / REDO
    # --------------------------------------------------
    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                img = self.history.undo(self.sketch_image)
                if img is not None:
                    self.sketch_image = img
                    self.edit.set_base_image(self.sketch_image)   # <<< EZ HIÁNYZIK
                    self.render_with_edit()
                return

            if event.key() == Qt.Key.Key_Y:
                img = self.history.redo(self.sketch_image)
                if img is not None:
                    self.sketch_image = img
                    self.edit.set_base_image(self.sketch_image)   # <<< EZ IS
                    self.render_with_edit()
                return


        super().keyPressEvent(event)

    def fit_to_view(self, img_w, img_h):
        view = self.scroll.viewport().size()

        if view.width() == 0 or view.height() == 0:
            return 1.0

        scale_w = view.width() / img_w
        scale_h = view.height() / img_h
        scale = min(scale_w, scale_h)

        # csak lefelé skálázunk
        return min(1.0, scale)

    # -------- VECTOR SLIDER FRISSÍTÉS --------
    def _update_vectorizer_params(self):
        if not hasattr(self, "vectorizer"):
            return

        d = self.vec_detail.value()
        m = self.vec_merge.value()
        s = self.vec_smooth.value()

        # 0..100 -> belső értékek
        self.vectorizer.min_length = 2 + (100 - d) * 0.25
        self.vectorizer.merge_dist = 1 + m * 0.08
        self.vectorizer.epsilon = 0.5 + s * 0.04

# ---------------- RUN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
