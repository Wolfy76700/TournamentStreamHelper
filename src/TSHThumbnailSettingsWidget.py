from email.policy import default
from multiprocessing import Lock
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
from pathlib import Path
import sys
import os

from .thumbnail import main_generate_thumbnail as thumbnail
from .SettingsManager import *
from .TSHGameAssetManager import *
from .Workers import Worker
from .Helpers.TSHDictHelper import deep_get, deep_set


class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Ignored
        )
        self._pixmap: QPixmap = None

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.repaint()

    def resizeEvent(self, QResizeEvent):
        self.repaint()
    
    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
    
    def drawWidget(self, qp: QPainter):
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.width()-64,
                self.height()-64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            qp.drawPixmap(int((self.width()-scaled.width())/2), int((self.height()-scaled.height())/2), scaled)

            if scaled.width() > 512:
                mini = self._pixmap.scaledToWidth(256)
                qp.drawPixmap(self.width()-mini.width(), self.height()-mini.height(), mini)


class TSHThumbnailSettingsWidgetSignals(QObject):
    updatePreview = pyqtSignal(str)


class TSHThumbnailSettingsWidget(QDockWidget):
    def __init__(self, *args):
        super().__init__(*args)

        if not SettingsManager.Get("thumbnail"):
            SettingsManager.Set("thumbnail", {})

        self.signals = TSHThumbnailSettingsWidgetSignals()
        self.signals.updatePreview.connect(self.UpdatePreview)

        self.thumbnailGenerationThread = QThreadPool()
        self.lock = Lock()

        self.setWindowTitle(QApplication.translate("app","Thumbnail Settings"))
        self.setFloating(True)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.widget = QWidget()
        self.setWidget(self.widget)
        self.widget.setLayout(QVBoxLayout())

        self.settings = uic.loadUi("src/layout/TSHThumbnailSettings.ui")
        self.widget.layout().addWidget(self.settings)

        # SET DEFAULTS
        self.setDefaultsButton = self.settings.findChild(
            QPushButton, "resetToDefault")
        self.setDefaultsButton.clicked.connect(
            lambda: self.setDefaults(button_mode=True))

        # IMG
        self.foreground = self.settings.findChild(
            QPushButton, "customForeground")
        self.background = self.settings.findChild(
            QPushButton, "customBackground")
        self.mainIcon = self.settings.findChild(QPushButton, "customMainIcon")
        self.topLeftIcon = self.settings.findChild(
            QPushButton, "customTopLeftIcon")
        self.topRightIcon = self.settings.findChild(
            QPushButton, "customTopRightIcon")

        self.foreground.clicked.connect(
            lambda: self.SaveImage("foreground_path"))
        self.background.clicked.connect(
            lambda: self.SaveImage("background_path"))

        if not self.GetSetting("main_icon_path", None):
            self.SaveSettings("main_icon_path", "./assets/icons/icon.png")
        self.mainIcon.clicked.connect(lambda: self.SaveImage("main_icon_path"))

        if not self.GetSetting("side_icon_list.L", None):
            self.SaveSettings("side_icon_list.L", "")
        self.topLeftIcon.clicked.connect(
            lambda: self.SaveIcons("side_icon_list", "L"))

        if not self.GetSetting("side_icon_list.R", None):
            self.SaveSettings("side_icon_list.R", "")
        self.topRightIcon.clicked.connect(
            lambda: self.SaveIcons("side_icon_list", "R"))

        self.templateSelect: QComboBox = self.settings.findChild(
            QComboBox, "templateSelect"
        )

        types = [f'./assets/thumbnail_base/thumbnail_types/{t}' for t in os.listdir("./assets/thumbnail_base/thumbnail_types/") if t.endswith(".json")]
        types.sort()
        self.templates = []
        for t in types:
            try:
                config = json.load(open(t))
                config["filename"] = t
                self.templates.append(config)
            except Exception as e:
                print(e)
        
        for t in self.templates:
            self.templateSelect.addItem(t.get("name") + f' ({t.get("filename", "").rsplit("/")[-1]})', t)
        
        currSettings = SettingsManager.Get("thumbnail", {})

        try:
            for i, t in enumerate(self.templates):
                if t.get("filename") == self.GetSetting("thumbnail_type", "./assets/thumbnail_base/thumbnail_types/type_a.json"):
                    self.templateSelect.setCurrentIndex(i)
        except:
            print(traceback.format_exc())
        
        self.templateSelect.currentIndexChanged.connect(
            lambda val: [
                TSHThumbnailSettingsWidget.SaveSettings(
                    self,
                    key=f"foreground_path", 
                    val=""
                ),
                TSHThumbnailSettingsWidget.SaveSettings(
                    self,
                    key=f"background_path", 
                    val=""
                ),
                TSHThumbnailSettingsWidget.SaveSettings(
                    self,
                    key=f"thumbnail_type", 
                    val=self.templateSelect.currentData().get("filename"),
                    generatePreview=True
                )
            ]
        )

        # SEPARATORS
        self.VSpacer = self.settings.findChild(QSpinBox, "widthSpacer")
        self.VColor = self.settings.findChild(QPushButton, "colorSpacer")

        self.VSpacer.valueChanged.connect(
            lambda: self.SaveSettings(
                key="separator.width",
                val=self.VSpacer.value(),
                generatePreview=True
            )
        )
        # open color select & save
        self.VColor.clicked.connect(
            lambda: self.ColorPicker(
                self.VColor,
                key="separator.color"
            )
        )

        # CHECKBOX
        self.phase_name = self.settings.findChild(QCheckBox, "phaseNameCheck")
        self.team_name = self.settings.findChild(QCheckBox, "teamNameCheck")
        self.sponsor = self.settings.findChild(QCheckBox, "sponsorCheck")
        self.smooth_scale = self.settings.findChild(QCheckBox, "smoothScaling")
        self.flip_p2 = self.settings.findChild(QCheckBox, "flipP2Check")
        self.flip_p1 = self.settings.findChild(QCheckBox, "flipP1Check")
        self.open_explorer = self.settings.findChild(QCheckBox, "openExplorerCheck")

        self.zoom = self.settings.findChild(QSpinBox, "zoom")

        self.horizontalAlign = self.settings.findChild(QSpinBox, "horizontalAlign")
        self.verticalAlign = self.settings.findChild(QSpinBox, "verticalAlign")

        self.scaleToFillX = self.settings.findChild(QCheckBox, "scaleToFillX")
        self.scaleToFillY = self.settings.findChild(QCheckBox, "scaleToFillY")

        self.hideSeparators = self.settings.findChild(QCheckBox, "hideSeparators")

        self.flipSeparators = self.settings.findChild(QCheckBox, "flipSeparators")

        self.phase_name.setChecked(self.GetSetting("display_phase", True))
        self.phase_name.stateChanged.connect(lambda: self.SaveSettings(
            key="display_phase", val=self.phase_name.isChecked(), generatePreview=True))

        self.team_name.setChecked(self.GetSetting("use_team_names", True))
        self.team_name.stateChanged.connect(lambda: self.SaveSettings(
            key="use_team_names", val=self.team_name.isChecked(), generatePreview=True))

        self.sponsor.setChecked(self.GetSetting("use_sponsors", True))
        self.sponsor.stateChanged.connect(lambda: self.SaveSettings(
            key="use_sponsors", val=self.sponsor.isChecked(), generatePreview=True))

        self.open_explorer.setChecked(self.GetSetting("open_explorer", False))
        self.open_explorer.stateChanged.connect(lambda: self.SaveSettings(
            key="open_explorer", val=self.open_explorer.isChecked(), generatePreview=True))
        
        self.flip_p2.stateChanged.connect(lambda: self.SaveSettings(
            key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.flip_p2", val=self.flip_p2.isChecked(), generatePreview=True))

        self.flip_p1.stateChanged.connect(lambda: self.SaveSettings(
            key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.flip_p1", val=self.flip_p1.isChecked(), generatePreview=True))
        
        self.smooth_scale.stateChanged.connect(lambda: self.SaveSettings(
            key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.smooth_scale", val=self.smooth_scale.isChecked(), generatePreview=True))

        self.zoom.valueChanged.connect(lambda:
            TSHThumbnailSettingsWidget.SaveSettings(
                self,
                key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.zoom",
                val=self.zoom.value(),
                generatePreview=True
            )
        )

        self.horizontalAlign.valueChanged.connect(lambda val: [
            TSHThumbnailSettingsWidget.SaveSettings(
                self,
                key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.align.horizontal", 
                val=val,
                generatePreview=True
            )]
        )
        
        self.verticalAlign.valueChanged.connect(lambda val: [
            TSHThumbnailSettingsWidget.SaveSettings(
                self,
                key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.align.vertical", 
                val=val,
                generatePreview=True
            )]
        )

        self.scaleToFillX.stateChanged.connect(lambda val: [
            TSHThumbnailSettingsWidget.SaveSettings(
                self,
                key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.scaleFillX", 
                val=self.scaleToFillX.checkState(),
                generatePreview=True
            )]
        )

        self.scaleToFillY.stateChanged.connect(lambda val: [
            TSHThumbnailSettingsWidget.SaveSettings(
                self,
                key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.scaleFillY", 
                val=self.scaleToFillY.checkState(),
                generatePreview=True
            )]
        )

        self.hideSeparators.stateChanged.connect(lambda val: [
            TSHThumbnailSettingsWidget.SaveSettings(
                self,
                key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.hideSeparators", 
                val=self.hideSeparators.checkState(),
                generatePreview=True
            )]
        )

        self.flipSeparators.stateChanged.connect(lambda val: [
            TSHThumbnailSettingsWidget.SaveSettings(
                self,
                key=f"game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.flipSeparators", 
                val=self.flipSeparators.checkState(),
                generatePreview=True
            )]
        )

        # FONTS
        self.selectFontPlayer = self.settings.findChild(
            QComboBox, "comboBoxFont")
        self.selectTypeFontPlayer = self.settings.findChild(
            QComboBox, "comboBoxFontType")
        self.selectFontPhase = self.settings.findChild(
            QComboBox, "comboBoxFontPhase")
        self.selectTypeFontPhase = self.settings.findChild(
            QComboBox, "comboBoxFontTypePhase")
        self.playerFontColor = self.settings.findChild(
            QPushButton, "colorPlayerFontColor")
        self.sponsorFontColor1 = self.settings.findChild(
            QPushButton, "sponsorFontColor1")
        self.sponsorFontColor2 = self.settings.findChild(
            QPushButton, "sponsorFontColor2")
        self.phaseFontColor = self.settings.findChild(
            QPushButton, "colorPhaseFontColor")
        self.colorPlayerOutline = self.settings.findChild(
            QPushButton, "colorPlayerOutline")
        self.colorPhaseOutline = self.settings.findChild(
            QPushButton, "colorPhaseOutline")
        self.enablePlayerOutline = self.settings.findChild(
            QCheckBox, "enablePlayerOutline")
        self.enablePhaseOutline = self.settings.findChild(
            QCheckBox, "enablePhaseOutline")

        self.playerFontColor.clicked.connect(lambda: [
            self.ColorPicker(button=self.playerFontColor, key="player_font_color"),
            self.GeneratePreview()
        ])
        self.sponsorFontColor1.clicked.connect(lambda: [
            self.ColorPicker(button=self.sponsorFontColor1, key="sponsor_font_color_1"),
            self.GeneratePreview()
        ])
        self.sponsorFontColor2.clicked.connect(lambda: [
            self.ColorPicker(button=self.sponsorFontColor2, key="sponsor_font_color_2"),
            self.GeneratePreview()
        ])
        self.phaseFontColor.clicked.connect(lambda: [
            self.ColorPicker(button=self.phaseFontColor, key="phase_font_color"),
            self.GeneratePreview()
        ])
        self.colorPlayerOutline.clicked.connect(lambda: [
            self.ColorPicker(button=self.colorPlayerOutline, key="player_outline_color"),
            self.GeneratePreview()
        ])
        self.colorPhaseOutline.clicked.connect(lambda: [
            self.ColorPicker(button=self.colorPhaseOutline, key="phase_outline_color"),
            self.GeneratePreview()
        ])
        self.enablePlayerOutline.stateChanged.connect(lambda: [
            self.SaveSettings("player_outline", val=self.enablePlayerOutline.isChecked()),
            self.updateFromSettings(),
            self.GeneratePreview()
        ])
        self.enablePhaseOutline.stateChanged.connect(lambda: [
            self.SaveSettings("phase_outline", val=self.enablePhaseOutline.isChecked()),
            self.updateFromSettings(),
            self.GeneratePreview()
        ])

        # PREVIEW
        previewContainer = self.settings.findChild(QWidget, "thumbnailPreview")
        self.preview = PreviewWidget()
        previewContainer.layout().addWidget(self.preview)

        self.updatePreview = self.settings.findChild(
            QPushButton, "btUpdatePreview")
        self.updatePreview.clicked.connect(lambda: self.GeneratePreview(True))
    
        self.generateThumbnail = self.settings.findChild(
            QPushButton, "btGenerate")
        self.generateThumbnail.clicked.connect(lambda: self.parent().scoreboard.GenerateThumbnail())

        # Load OpenSans
        QFontDatabase.addApplicationFont(
            "./assets/font/OpenSans/OpenSans-Bold.ttf")
        QFontDatabase.addApplicationFont(
            "./assets/font/OpenSans/OpenSans-Semibold.ttf")

        unloadable, self.family_to_path = self.getFontPaths()
        # add Open Sans
        self.family_to_path["Open Sans"] = [
            './assets/font/OpenSans/OpenSans-Bold.ttf',
            './assets/font/OpenSans/OpenSans-Semibold.ttf'
        ]

        # Load Roboto Condensed
        QFontDatabase.addApplicationFont(
            "./assets/font/RobotoCondensed.ttf")
        
        self.family_to_path["Roboto Condensed"] = [
            './assets/font/RobotoCondensed.ttf',
            './assets/font/RobotoCondensed.ttf'
        ]

        # add all fonts available
        for k, v in sorted(self.family_to_path.items()):
            self.selectFontPlayer.addItem(k, v)
            self.selectFontPhase.addItem(k, v)

        # listener
        self.selectFontPlayer.currentIndexChanged.connect(
            lambda: self.SetTypeFont(0, self.selectFontPlayer, self.selectTypeFontPlayer))
        self.selectFontPhase.currentIndexChanged.connect(
            lambda: self.SetTypeFont(1, self.selectFontPhase, self.selectTypeFontPhase))

        # listener type font
        self.selectTypeFontPlayer.currentIndexChanged.connect(lambda: self.SaveFont(
            "player_font",
            self.selectFontPlayer.currentText(),
            self.selectTypeFontPlayer.currentText(),
            self.selectTypeFontPlayer.currentData()
        ))
        self.selectTypeFontPhase.currentIndexChanged.connect(lambda: self.SaveFont(
            "phase_font",
            self.selectFontPhase.currentText(),
            self.selectTypeFontPhase.currentText(),
            self.selectTypeFontPhase.currentData()
        ))

        # Asset Pack
        self.selectRenderLabel = self.settings.findChild(QLabel, "label_asset")
        self.selectRenderType = self.settings.findChild(
            QComboBox, "comboBoxAsset")
        # add item (assets pack) when choosing game
        TSHGameAssetManager.instance.signals.onLoad.connect(lambda: [
            self.LoadAssetPacks(),
            self.updateFromSettings(),
            self.GeneratePreview()
        ])

        self.selectRenderType.currentIndexChanged.connect(lambda: [
            SettingsManager.Set(
                f"thumbnail.game.{TSHGameAssetManager.instance.selectedGame.get('codename')}.asset_pack",
                self.selectRenderType.currentData()
            ),
            self.updateFromSettings(),
            self.GeneratePreview()
        ])

        tmp_path = "./tmp/thumbnail"
        tmp_file = f"{tmp_path}/template.jpg"
        Path(tmp_path).mkdir(parents=True, exist_ok=True)

        # if preview not there
        if not os.path.isfile(tmp_file):
            try:
                tmp_file = thumbnail.generate(
                    isPreview=True, settingsManager=SettingsManager, gameAssetManager=TSHGameAssetManager)
            except Exception as e:
                self.DisplayErrorMessage(traceback.format_exc())
        self.preview.setPixmap(QPixmap(tmp_file))

        self.updateFromSettings()
    
    def GetSetting(self, key, default=0):
        setting = SettingsManager.Get(
            f"thumbnail.{key}",
            default=None
        )
        if setting == None:
            setting = default
            SettingsManager.Set(f"thumbnail.{key}", default)
        return setting
    
    def updateFromSettings(self):
        game_codename = TSHGameAssetManager.instance.selectedGame.get('codename')

        # Player font, player font type
        playerFont = self.GetSetting(
            "player_font",
            {
                "name": "Roboto Condensed",
                "type": "Bold",
                "fontPath": "./assets/font/RobotoCondensed.ttf"
            }
        )
        self.selectFontPlayer.setCurrentIndex(
            self.selectFontPlayer.findText(playerFont.get("name")))
        self.selectTypeFontPlayer.setCurrentIndex(
            self.selectTypeFontPlayer.findText(playerFont.get("type")))

        # Phase font, phase font type
        phaseFont = self.GetSetting(
            "phase_font",
            {
                "name": "Roboto Condensed",
                "type": "Bold",
                "fontPath": "./assets/font/RobotoCondensed.ttf"
            }
        )
        self.selectFontPhase.setCurrentIndex(
            self.selectFontPhase.findText(phaseFont.get("name")))
        self.selectTypeFontPhase.setCurrentIndex(
            self.selectTypeFontPhase.findText(phaseFont.get("type")))
        
        # Outlines
        self.enablePlayerOutline.blockSignals(True)
        self.enablePlayerOutline.setChecked(self.GetSetting(f"player_outline", True))
        self.enablePlayerOutline.blockSignals(False)
        
        self.enablePhaseOutline.blockSignals(True)
        self.enablePhaseOutline.setChecked(self.GetSetting(f"phase_outline", True))
        self.enablePhaseOutline.blockSignals(False)

        # Set background-color for color pickers
        if self.GetSetting("player_outline", True) == True:
            self.colorPlayerOutline.setStyleSheet("background-color: %s" % self.GetSetting("player_outline_color", "#000000"))
            self.colorPlayerOutline.setText("")
        else:
            self.colorPlayerOutline.setStyleSheet("")
            self.colorPlayerOutline.setText("Disabled")
        
        if self.GetSetting("phase_outline", True) == True:
            self.colorPhaseOutline.setStyleSheet("background-color: %s" % self.GetSetting("phase_outline_color", "#000000"))
            self.colorPhaseOutline.setText("")
        else:
            self.colorPhaseOutline.setStyleSheet("")
            self.colorPhaseOutline.setText("Disabled")
        
        self.playerFontColor.setStyleSheet("background-color: %s" % self.GetSetting("player_font_color", "#FFFFFF"))
        self.phaseFontColor.setStyleSheet("background-color: %s" % self.GetSetting("phase_font_color", "#FFFFFF"))

        self.sponsorFontColor1.setStyleSheet("background-color: %s" % self.GetSetting("sponsor_font_color_1", "#ff7a6d"))
        self.sponsorFontColor2.setStyleSheet("background-color: %s" % self.GetSetting("sponsor_font_color_2", "#29b6f6"))

        self.VColor.setStyleSheet("background-color: %s" % self.GetSetting("separator.color", "#000000"))

        # Separator width
        self.VSpacer.blockSignals(True)
        self.VSpacer.setValue(self.GetSetting(
            f"separator.width",
            6
        ))
        self.VSpacer.blockSignals(False)

        # Flip player assets
        self.flip_p2.blockSignals(True)
        self.flip_p2.setChecked(self.GetSetting(f"game.{game_codename}.flip_p2", True))
        self.flip_p2.blockSignals(False)

        self.flip_p1.blockSignals(True)
        self.flip_p1.setChecked(self.GetSetting(f"game.{game_codename}.flip_p1", False))
        self.flip_p1.blockSignals(False)

        self.smooth_scale.blockSignals(True)
        self.smooth_scale.setChecked(self.GetSetting(f"game.{game_codename}.smooth_scale", True))
        self.smooth_scale.blockSignals(False)

        # Eyesight alignment
        self.horizontalAlign.blockSignals(True)
        self.horizontalAlign.setValue(self.GetSetting(
            f"game.{game_codename}.align.horizontal",
            50
        ))
        self.horizontalAlign.blockSignals(False)

        self.verticalAlign.blockSignals(True)
        self.verticalAlign.setValue(self.GetSetting(
            f"game.{game_codename}.align.vertical",
            40
        ))
        self.verticalAlign.blockSignals(False)

        # Zoom
        self.zoom.blockSignals(True)
        self.zoom.setValue(self.GetSetting(
            f"game.{game_codename}.zoom",
            100
        ))
        self.zoom.blockSignals(False)

        # Flip separators
        self.flipSeparators.blockSignals(True)
        self.flipSeparators.setChecked(self.GetSetting(
            f"game.{game_codename}.flipSeparators",
            False
        ))
        self.flipSeparators.blockSignals(False)

        # Hide separators
        self.hideSeparators.blockSignals(True)
        self.hideSeparators.setChecked(self.GetSetting(
            f"game.{game_codename}.hideSeparators",
            False
        ))
        self.hideSeparators.blockSignals(False)

        # Scale to fill X/Y
        self.scaleToFillX.blockSignals(True)
        self.scaleToFillX.setChecked(self.GetSetting(
            f"game.{game_codename}.scaleFillX",
            False
        ))
        self.scaleToFillX.blockSignals(False)

        self.scaleToFillY.blockSignals(True)
        self.scaleToFillY.setChecked(self.GetSetting(
            f"game.{game_codename}.scaleFillY",
            False
        ))
        self.scaleToFillY.blockSignals(False)

        # Disable scale to fill options if it doesn't make sense with uncropped edge
        # Because if the edges are cropped it's going to scale to fill anyways
        # since we can't let it show past a cropped edge
        uncropped_edge = []

        if TSHGameAssetManager.instance.selectedGame.get("assets", {}).get(self.GetSetting(f"game.{game_codename}.asset_pack"), {}).get("uncropped_edge", []):
            uncropped_edge = TSHGameAssetManager.instance.selectedGame.get("assets").get(self.GetSetting(f"game.{game_codename}.asset_pack"), {}).get("uncropped_edge", [])

        if 'l' in uncropped_edge or 'r' in uncropped_edge:
            self.scaleToFillX.setEnabled(True)
            if self.GetSetting(f"game.{game_codename}.scaleFillX") == None:
                TSHThumbnailSettingsWidget.SaveSettings(self, key=f"scaleToFillX/{game_codename}", val=self.scaleToFillX.checkState(), generatePreview=False)
            self.scaleToFillX.setChecked(
                self.GetSetting(f"game.{game_codename}.scaleFillX", 0))
        else:
            self.scaleToFillX.setChecked(0)
            self.scaleToFillX.setEnabled(False)
        
        if 'u' in uncropped_edge or 'd' in uncropped_edge:
            self.scaleToFillY.setEnabled(True)
            if self.GetSetting(f"game.{game_codename}.scaleFillY") == None:
                TSHThumbnailSettingsWidget.SaveSettings(self, key=f"scaleToFillY/game.{game_codename}", val=self.scaleToFillY.checkState(), generatePreview=False)
            self.scaleToFillY.setChecked(
                self.GetSetting(f"game.{game_codename}.scaleFillY", 0))
        else:
            self.scaleToFillY.setChecked(0)
            self.scaleToFillY.setEnabled(False)
    
    def setDefaults(self, button_mode=False):
        pass

    def SaveIcons(self, key, side):
        path = QFileDialog.getOpenFileName()[0]
        if path:
            self.SaveSettings(key=f"{key}.{side}", val=path, generatePreview=True)

    def SaveImage(self, key):
        path = QFileDialog.getOpenFileName()[0]
        if path:
            self.SaveSettings(key=key, val=path, generatePreview=True)

    def SaveFont(self, key, font, type, fontPath):
        try:
            if font and fontPath:
                fontSetting = {
                    "name": font,
                    "type": type,
                    "fontPath": fontPath
                }
                self.SaveSettings(f"{key}", val=fontSetting)
        except Exception as e:
            print("error save font")
            print(e)

    def ColorPicker(self, button, key):
        try:
            # HEX color
            color_result = QColorDialog.getColor()
            if color_result.isValid():
                color = color_result.name()
                self.SaveSettings(f"{key}", val=color)
                self.updateFromSettings()
        except Exception as e:
            print(e)

    def SaveSettings(self, key, val, generatePreview=False):
        try:
            SettingsManager.Set(f"thumbnail.{key}", val)
        except Exception as e:
            print(e)

        if generatePreview:
            self.GeneratePreview()

    def SetTypeFont(self, index, cbFont, cbType):
        print(f'set type font {cbFont.currentData()}')
        types = ["Regular", "Bold", "Italic", "Bold Italic"]
        types_localised = ["Regular", "Bold", "Italic", "Bold Italic"]
        types_localised[0] = QApplication.translate("app","Regular")
        types_localised[1] = QApplication.translate("app","Bold")
        types_localised[2] = QApplication.translate("app","Italic")
        types_localised[3] = QApplication.translate("app","Bold Italic")

        cbType.clear()

        for i in range(len(types)):
            cbType.addItem(types_localised[i], types[i])

    def getFontPaths(self):
        font_paths = QStandardPaths.standardLocations(
            QStandardPaths.FontsLocation)
        if sys.platform == "win32":
            font_paths.append(
                f"{os.getenv('LOCALAPPDATA')}\\Microsoft\\Windows\\Fonts")

        unloadable = []
        family_to_path = {}

        db = QFontDatabase()
        for fpath in font_paths:  # go through all font paths
            if os.path.exists(fpath):
                # go through all files at each path
                for root, dirs, files in os.walk(fpath):
                    for file in files:
                        path = os.path.join(root, file)

                        idx = db.addApplicationFont(path)  # add font path

                        if idx < 0:
                            # font wasn't loaded if idx is -1
                            unloadable.append(path)
                        else:
                            names = db.applicationFontFamilies(
                                idx)  # load back font family name

                            for n in names:
                                if n in family_to_path:
                                    family_to_path[n].append(path)
                                else:
                                    family_to_path[n] = [path]
                            # this isn't a 1:1 mapping, for example
                            # 'C:/Windows/Fonts/HTOWERT.TTF' (regular) and
                            # 'C:/Windows/Fonts/HTOWERTI.TTF' (italic) are different
                            # but applicationFontFamilies will return 'High Tower Text' for both
        return unloadable, family_to_path

    # re-generate preview
    def GeneratePreview(self, manual=False):
        SettingsManager.LoadSettings()

        if not manual:
            # Automatic preview update, we dont want it to spam error messages
            try:
                worker = Worker(self.GeneratePreviewDo)
                self.thumbnailGenerationThread.start(worker)
            except Exception as e:
                pass
        else:
            # Manually clicked the update button
            try:
                tmp_file = thumbnail.generate(
                    isPreview=True, settingsManager=SettingsManager, gameAssetManager=TSHGameAssetManager)
                if tmp_file:
                    self.signals.updatePreview.emit(tmp_file)
            except Exception as e:
                self.DisplayErrorMessage(traceback.format_exc())

    def GeneratePreviewDo(self, progress_callback):
        with self.lock:
            try:
                tmp_file = thumbnail.generate(
                    isPreview=True, settingsManager=SettingsManager, gameAssetManager=TSHGameAssetManager)
                if tmp_file:
                    self.signals.updatePreview.emit(tmp_file)
            except Exception as e:
                pass
    
    def DisplayErrorMessage(self, e):
        print(e)
        msgBox = QMessageBox()
        msgBox.setWindowIcon(QIcon('assets/icons/icon.png'))
        msgBox.setWindowTitle(QApplication.translate("thumb_app", "TSH - Thumbnail"))
        msgBox.setText(QApplication.translate("app", "Warning"))
        msgBox.setInformativeText(str(e))
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.exec()

    def UpdatePreview(self, file):
        self.preview.setPixmap(QPixmap(file))
    
    def LoadAssetPacks(self):
        self.selectRenderType.blockSignals(True)

        self.selectRenderLabel.setText("(No game selected)")
        self.selectRenderType.clear()

        if TSHGameAssetManager.instance.selectedGame.get("assets"):
            asset_dict = {}
            for key, val in TSHGameAssetManager.instance.selectedGame.get("assets").items():
                # don't use base_files, because don't contains asset, only folder (?)
                if key == "base_files":
                    continue
                # Skip stage icon assets
                if isinstance(val.get("type"), list) and "stage_icon" in val.get("type"):
                    continue
                if val.get("name"):
                    self.selectRenderType.addItem(val.get("name"), key)
                    asset_dict[key] = val.get("name")
                else:
                    self.selectRenderType.addItem(key, key)
                    asset_dict[key] = key

            game_codename = TSHGameAssetManager.instance.selectedGame.get("codename")

            self.selectRenderLabel.setText(f"{game_codename}")

            asset_pack = self.GetSetting(f"game.{game_codename}.asset_pack", "full")
            index = self.selectRenderType.findText(asset_dict.get(SettingsManager.Get(f"thumbnail.game.{game_codename}.asset_pack")))

            if index != -1:
                self.selectRenderType.setCurrentIndex(index)

        self.selectRenderType.blockSignals(False)