from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic

from TSHScoreboardPlayerWidget import *
from SettingsManager import *
from StateManager import *
from TSHTournamentDataProvider import TSHTournamentDataProvider
from TSHScoreboardStageWidget import TSHScoreboardStageWidget


class TSHScoreboardWidgetSignals(QObject):
    UpdateSetData = pyqtSignal(object)
    NewSetSelected = pyqtSignal(object)


class TSHScoreboardWidget(QDockWidget):
    def __init__(self, *args):
        super().__init__(*args)

        self.signals = TSHScoreboardWidgetSignals()
        self.signals.UpdateSetData.connect(self.UpdateSetData)
        self.signals.NewSetSelected.connect(self.NewSetSelected)

        self.lastSetSelected = None

        self.autoUpdateTimer: QTimer = None
        self.timeLeftTimer: QTimer = None

        self.setWindowTitle("Scoreboard")
        self.setFloating(True)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.widget = QWidget()
        self.setWidget(self.widget)
        self.widget.setLayout(QVBoxLayout())

        self.tabs = QTabWidget()
        self.widget.layout().addWidget(self.tabs)

        self.tabScore = QWidget()

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.tabScore)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setStyleSheet(
            "QTabWidget::pane { margin: 0px,0px,0px,0px }")

        self.tabScore.setLayout(QVBoxLayout())
        self.tabs.addTab(self.scrollArea, "Score")
        self.tabStage = QWidget()
        self.tabStage.setLayout(QVBoxLayout())
        self.tabs.addTab(self.tabStage, "Stage")
        self.tabStage.layout().addWidget(TSHScoreboardStageWidget())

        # StateManager.Set("score", {})

        self.setFloating(True)
        self.setWindowFlags(Qt.WindowType.Window)

        topOptions = QWidget()
        topOptions.setLayout(QHBoxLayout())
        topOptions.layout().setSpacing(0)
        topOptions.layout().setContentsMargins(0, 0, 0, 0)
        topOptions.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)

        self.tabScore.layout().addWidget(topOptions)

        col = QWidget()
        col.setLayout(QVBoxLayout())
        topOptions.layout().addWidget(col)
        col.setContentsMargins(0, 0, 0, 0)
        col.layout().setSpacing(0)
        self.charNumber = QSpinBox()
        col.layout().addWidget(QLabel("Characters per player"))
        col.layout().addWidget(self.charNumber)
        self.charNumber.valueChanged.connect(self.SetCharacterNumber)

        col = QWidget()
        col.setLayout(QVBoxLayout())
        topOptions.layout().addWidget(col)
        col.setContentsMargins(0, 0, 0, 0)
        col.layout().setSpacing(0)
        self.playerNumber = QSpinBox()
        col.layout().addWidget(QLabel("Players per team"))
        col.layout().addWidget(self.playerNumber)
        self.playerNumber.valueChanged.connect(self.SetPlayersPerTeam)

        col = QWidget()
        col.setLayout(QVBoxLayout())
        col.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        col.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        topOptions.layout().addWidget(col)
        col.setContentsMargins(0, 0, 0, 0)
        col.layout().setSpacing(0)
        self.eyeBt = QToolButton()
        self.eyeBt.setIcon(QIcon('icons/eye.svg'))
        self.eyeBt.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Fixed)
        col.layout().addWidget(self.eyeBt, Qt.AlignmentFlag.AlignRight)
        self.eyeBt.setPopupMode(QToolButton.InstantPopup)
        self.eyeBt.setMenu(QMenu())

        self.eyeBt.menu().addSection("Players")

        elements = [
            ["Real Name", ["real_name", "real_nameLabel"]],
            ["Twitter", ["twitter", "twitterLabel"]],
            ["Location", ["locationLabel", "state", "country"]],
            ["Characters", ["characters"]]
        ]
        for element in elements:
            action: QAction = self.eyeBt.menu().addAction(element[0])
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(
                lambda toggled, action=action, element=element: self.ToggleElements(action, element[1]))

        self.eyeBt.menu().addSection("Match data")
        action: QAction = self.eyeBt.menu().addAction("Test")

        self.playerWidgets = []
        self.team1playerWidgets = []
        self.team2playerWidgets = []

        self.team1swaps = []
        self.team2swaps = []

        self.columns = QWidget()
        self.columns.setLayout(QHBoxLayout())
        self.tabScore.layout().addWidget(self.columns)

        bottomOptions = QWidget()
        bottomOptions.setLayout(QVBoxLayout())
        bottomOptions.layout().setContentsMargins(0, 0, 0, 0)
        bottomOptions.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)

        self.tabScore.layout().addWidget(bottomOptions)

        self.btSelectSet = QPushButton("Load set")
        self.btSelectSet.setEnabled(False)
        bottomOptions.layout().addWidget(self.btSelectSet)
        self.btSelectSet.clicked.connect(self.LoadSetClicked)

        hbox = QHBoxLayout()
        bottomOptions.layout().addLayout(hbox)

        self.btLoadStreamSet = QPushButton("Load current stream set")
        self.btLoadStreamSet.setIcon(QIcon("./icons/twitch.svg"))
        self.btLoadStreamSet.setEnabled(False)
        hbox.addWidget(self.btLoadStreamSet)
        self.btLoadStreamSet.clicked.connect(self.LoadStreamSetClicked)
        TSHTournamentDataProvider.instance.signals.twitch_username_updated.connect(
            self.UpdateStreamButton)

        self.btLoadStreamSetOptions = QPushButton()
        self.btLoadStreamSetOptions.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.btLoadStreamSetOptions.setIcon(QIcon("./icons/settings.svg"))
        self.btLoadStreamSetOptions.clicked.connect(
            self.LoadStreamSetOptionsClicked)
        hbox.addWidget(self.btLoadStreamSetOptions)

        hbox = QHBoxLayout()
        bottomOptions.layout().addLayout(hbox)

        self.btLoadPlayerSet = QPushButton("Load player set")
        self.btLoadPlayerSet.setEnabled(False)
        self.btLoadPlayerSet.clicked.connect(self.LoadUserSetClicked)
        hbox.addWidget(self.btLoadPlayerSet)
        TSHTournamentDataProvider.instance.signals.user_updated.connect(
            self.UpdateUserSetButton)
        TSHTournamentDataProvider.instance.signals.tournament_changed.connect(
            self.UpdateUserSetButton)

        self.btLoadPlayerSetOptions = QPushButton()
        self.btLoadPlayerSetOptions.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.btLoadPlayerSetOptions.setIcon(QIcon("./icons/settings.svg"))
        self.btLoadPlayerSetOptions.clicked.connect(
            self.LoadUserSetOptionsClicked)
        hbox.addWidget(self.btLoadPlayerSetOptions)

        TSHTournamentDataProvider.instance.signals.tournament_changed.connect(
            self.UpdateBottomButtons)
        TSHTournamentDataProvider.instance.signals.tournament_changed.emit()

        self.timerLayout = QWidget()
        self.timerLayout.setLayout(QHBoxLayout())
        self.timerLayout.layout().setContentsMargins(0, 0, 0, 0)
        self.timerLayout.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.timerLayout.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottomOptions.layout().addWidget(self.timerLayout)
        self.labelAutoUpdate = QLabel("Auto update")
        self.timerLayout.layout().addWidget(self.labelAutoUpdate)
        self.timerTime = QLabel("0")
        self.timerLayout.layout().addWidget(self.timerTime)
        self.timerCancelBt = QPushButton()
        self.timerCancelBt.setIcon(QIcon('icons/cancel.svg'))
        self.timerCancelBt.setIconSize(QSize(12, 12))
        self.timerCancelBt.clicked.connect(self.StopAutoUpdate)
        self.timerLayout.layout().addWidget(self.timerCancelBt)
        self.timerLayout.setVisible(False)

        self.team1column = uic.loadUi("src/layout/TSHScoreboardTeam.ui")
        self.columns.layout().addWidget(self.team1column)
        self.team1column.findChild(QLabel, "teamLabel").setText("TEAM 1")
        self.team1column.findChild(QScrollArea).setWidget(QWidget())
        self.team1column.findChild(
            QScrollArea).widget().setLayout(QVBoxLayout())

        for c in self.team1column.findChildren(QLineEdit):
            c.textChanged.connect(
                lambda text, element=c: [
                    StateManager.Set(
                        f"score.team.1.{element.objectName()}", text)
                ])
            c.textChanged.emit("")

        for c in self.team1column.findChildren(QCheckBox):
            c.toggled.connect(
                lambda state, element=c: [
                    StateManager.Set(
                        f"score.team.1.{element.objectName()}", state)
                ])
            c.toggled.emit(False)

        self.scoreColumn = uic.loadUi("src/layout/TSHScoreboardScore.ui")
        self.columns.layout().addWidget(self.scoreColumn)

        self.team2column = uic.loadUi("src/layout/TSHScoreboardTeam.ui")
        self.columns.layout().addWidget(self.team2column)
        self.team2column.findChild(QLabel, "teamLabel").setText("TEAM 2")
        self.team2column.findChild(QScrollArea).setWidget(QWidget())
        self.team2column.findChild(
            QScrollArea).widget().setLayout(QVBoxLayout())

        for c in self.team2column.findChildren(QLineEdit):
            c.textChanged.connect(
                lambda text, element=c: [
                    StateManager.Set(
                        f"score.team.2.{element.objectName()}", text)
                ])
            c.textChanged.emit("")

        for c in self.team2column.findChildren(QCheckBox):
            c.toggled.connect(
                lambda state, element=c: [
                    StateManager.Set(
                        f"score.team.2.{element.objectName()}", state)
                ])
            c.toggled.emit(False)

        StateManager.Unset(f'score.team.1.players')
        StateManager.Unset(f'score.team.2.players')
        StateManager.Unset(f'score.stage_strike')
        self.playerNumber.setValue(1)
        self.charNumber.setValue(1)

        for c in self.scoreColumn.findChildren(QComboBox):
            c.editTextChanged.connect(
                lambda text, element=c: [
                    StateManager.Set(
                        f"score.{element.objectName()}", element.currentText())
                ]
            )
            c.editTextChanged.emit("")
            c.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.scoreColumn.findChild(QSpinBox, "best_of").valueChanged.connect(
            lambda value: StateManager.Set(
                f"score.best_of", value)
        )
        self.scoreColumn.findChild(QSpinBox, "best_of").valueChanged.emit(0)

        self.scoreColumn.findChild(QSpinBox, "score_left").valueChanged.connect(
            lambda value: StateManager.Set(
                f"score.team.1.score", value)
        )
        self.scoreColumn.findChild(
            QSpinBox, "score_left").valueChanged.emit(0)

        self.scoreColumn.findChild(QSpinBox, "score_right").valueChanged.connect(
            lambda value: StateManager.Set(
                f"score.team.2.score", value)
        )
        self.scoreColumn.findChild(
            QSpinBox, "score_right").valueChanged.emit(0)

        self.team1column.findChild(QLineEdit, "teamName").textChanged.connect(
            lambda value: self.ExportTeamLogo("1", value)
        )
        self.team2column.findChild(QLineEdit, "teamName").textChanged.connect(
            lambda value: self.ExportTeamLogo("2", value)
        )

        self.teamsSwapped = False

        self.scoreColumn.findChild(
            QPushButton, "btSwapTeams").clicked.connect(self.SwapTeams)

        self.scoreColumn.findChild(
            QPushButton, "btResetScore").clicked.connect(self.ResetScore)

    def ExportTeamLogo(self, team, value):
        if os.path.exists(f"./team_logo/{value.lower()}.png"):
            StateManager.Set(f"score.team.{team}.logo",
                             f"./team_logo/{value.lower()}.png")
        else:
            StateManager.Set(f"score.team.{team}.logo", None)

    def ToggleElements(self, action: QAction, elements: list[QWidget]):
        for pw in self.playerWidgets:
            for element in elements:
                pw.findChild(QWidget, element).setVisible(action.isChecked())

    def UpdateBottomButtons(self):
        if TSHTournamentDataProvider.instance.provider and TSHTournamentDataProvider.instance.provider.url:
            self.btSelectSet.setText(
                "Load set from "+TSHTournamentDataProvider.instance.provider.url)
            self.btSelectSet.setEnabled(True)
            self.btLoadStreamSet.setEnabled(True)
            self.btLoadPlayerSet.setEnabled(True)
        else:
            self.btSelectSet.setText(
                "Load set")
            self.btSelectSet.setEnabled(False)

    def SetCharacterNumber(self, value):
        for pw in self.playerWidgets:
            pw.SetCharactersPerPlayer(value)

    def SetPlayersPerTeam(self, number):
        while len(self.team1playerWidgets) < number:
            p = TSHScoreboardPlayerWidget(
                index=len(self.team1playerWidgets)+1, teamNumber=1, path=f'score.team.{1}.players.{len(self.team1playerWidgets)+1}')
            self.playerWidgets.append(p)
            print(self.team1column.findChild(QScrollArea))
            self.team1column.findChild(
                QScrollArea).widget().layout().addWidget(p)
            p.SetCharactersPerPlayer(self.charNumber.value())
            self.team1column.findChild(
                QCheckBox, "losers").toggled.connect(p.SetLosers)

            index = len(self.team1playerWidgets)

            p.btMoveUp.clicked.connect(lambda x, index=index, p=p: p.SwapWith(
                self.team1playerWidgets[index-1]))
            p.btMoveDown.clicked.connect(lambda x, index=index, p=p: p.SwapWith(
                self.team1playerWidgets[index+1]))
            self.team1playerWidgets.append(p)

            p = TSHScoreboardPlayerWidget(
                index=len(self.team2playerWidgets)+1, teamNumber=2, path=f'score.team.{2}.players.{len(self.team2playerWidgets)+1}')
            self.playerWidgets.append(p)
            self.team2column.findChild(
                QScrollArea).widget().layout().addWidget(p)
            p.SetCharactersPerPlayer(self.charNumber.value())
            self.team2column.findChild(
                QCheckBox, "losers").toggled.connect(p.SetLosers)

            index = len(self.team2playerWidgets)

            p.btMoveUp.clicked.connect(lambda x, index=index, p=p: p.SwapWith(
                self.team2playerWidgets[index-1]))
            p.btMoveDown.clicked.connect(lambda x, index=index, p=p: p.SwapWith(
                self.team2playerWidgets[index+1]))
            self.team2playerWidgets.append(p)

        while len(self.team1playerWidgets) > number:
            team1player = self.team1playerWidgets[-1]
            team1player.setParent(None)
            self.playerWidgets.remove(team1player)
            self.team1playerWidgets.remove(team1player)

            team2player = self.team2playerWidgets[-1]
            team2player.setParent(None)
            self.playerWidgets.remove(team2player)
            self.team2playerWidgets.remove(team2player)

        for team in [1, 2]:
            if StateManager.Get(f'score.team.{team}'):
                for k in list(StateManager.Get(f'score.team.{team}.players').keys()):
                    if not k.isnumeric() or (k.isnumeric() and int(k) > number):
                        StateManager.Unset(f'score.team.{team}.players.{k}')

        if number > 1:
            self.team1column.findChild(QLineEdit, "teamName").setVisible(True)
            self.team2column.findChild(QLineEdit, "teamName").setVisible(True)
        else:
            self.team1column.findChild(QLineEdit, "teamName").setVisible(False)
            self.team1column.findChild(QLineEdit, "teamName").setText("")
            self.team2column.findChild(QLineEdit, "teamName").setVisible(False)
            self.team2column.findChild(QLineEdit, "teamName").setText("")

    def SwapTeams(self):
        tmpData = [[], []]

        # Save state
        for t, team in enumerate([self.team1playerWidgets, self.team2playerWidgets]):
            for i, p in enumerate(team):
                data = {}
                for widget in p.findChildren(QWidget):
                    if type(widget) == QLineEdit:
                        data[widget.objectName()] = widget.text()
                    if type(widget) == QComboBox:
                        data[widget.objectName()] = widget.currentIndex()
                data["online_avatar"] = StateManager.Get(
                    f"score.team.{t+1}.players.{i+1}.online_avatar")
                data["id"] = StateManager.Get(
                    f"score.team.{t+1}.players.{i+1}.id")
                tmpData[t].append(data)

        # Load state
        for t, team in enumerate([self.team2playerWidgets, self.team1playerWidgets]):
            for i, p in enumerate(tmpData[t]):
                for objName in tmpData[t][i]:
                    widget = team[i].findChild(QWidget, objName)
                    if widget:
                        if type(widget) == QLineEdit:
                            widget.setText(tmpData[t][i][objName])
                        if type(widget) == QComboBox:
                            widget.setCurrentIndex(tmpData[t][i][objName])
                QCoreApplication.processEvents()
                team[i].ExportPlayerImages(tmpData[t][i]["online_avatar"])
                team[i].ExportPlayerId(tmpData[t][i]["id"])

        # Scores
        scoreLeft = self.scoreColumn.findChild(QSpinBox, "score_left").value()
        self.scoreColumn.findChild(QSpinBox, "score_left").setValue(
            self.scoreColumn.findChild(QSpinBox, "score_right").value())
        self.scoreColumn.findChild(QSpinBox, "score_right").setValue(scoreLeft)

        # Losers
        losersLeft = self.team1column.findChild(
            QCheckBox, "losers").isChecked()
        self.team1column.findChild(QCheckBox, "losers").setChecked(
            self.team2column.findChild(QCheckBox, "losers").isChecked())
        self.team2column.findChild(QCheckBox, "losers").setChecked(losersLeft)

        self.teamsSwapped = not self.teamsSwapped

    def ResetScore(self):
        self.scoreColumn.findChild(QComboBox, "match").setCurrentText("")
        self.scoreColumn.findChild(QComboBox, "phase").setCurrentText("")
        self.scoreColumn.findChild(QSpinBox, "score_left").setValue(0)
        self.scoreColumn.findChild(QSpinBox, "score_right").setValue(0)

    def NewSetSelected(self, data):
        self.StopAutoUpdate()
        self.autoUpdateTimer = QTimer()
        self.autoUpdateTimer.start(5000)
        self.timeLeftTimer = QTimer()
        self.timeLeftTimer.start(100)
        self.timeLeftTimer.timeout.connect(self.UpdateTimeLeftTimer)
        self.timerLayout.setVisible(True)

        if data and data.get("id"):
            if data.get("id") != self.lastSetSelected:
                StateManager.Unset(f'score.stage_strike')
                self.lastSetSelected = data.get("id")
                self.ClearScore()

                if data and data.get("id"):
                    TSHTournamentDataProvider.instance.GetMatch(
                        self, data["id"], overwrite=True)

                self.autoUpdateTimer.timeout.connect(
                    lambda setId=data: TSHTournamentDataProvider.instance.GetMatch(self, data.get("id"), overwrite=False))
            else:
                TSHTournamentDataProvider.instance.GetMatch(
                    self, data["id"], overwrite=False)

        if data.get("auto_update") == "stream":
            self.autoUpdateTimer.timeout.connect(
                lambda setId=data: TSHTournamentDataProvider.instance.LoadStreamSet(self, SettingsManager.Get("twitch_username")))

        if data.get("auto_update") == "user":
            self.autoUpdateTimer.timeout.connect(
                lambda setId=data: TSHTournamentDataProvider.instance.LoadUserSet(
                    self, SettingsManager.Get(TSHTournamentDataProvider.instance.provider.name+"_user")))

            # Force user to be P1
            if data.get("reverse") and not self.teamsSwapped:
                self.SwapTeams()
            elif not data.get("reverse") and self.teamsSwapped:
                self.SwapTeams()

    def StopAutoUpdate(self):
        if self.autoUpdateTimer != None:
            self.autoUpdateTimer.stop()
            self.autoUpdateTimer = None
        if self.timeLeftTimer != None:
            self.timeLeftTimer.stop()
            self.timeLeftTimer = None
        self.timerLayout.setVisible(False)

    def UpdateTimeLeftTimer(self):
        if self.autoUpdateTimer:
            self.timerTime.setText(
                str(int(self.autoUpdateTimer.remainingTime()/1000)))

    def LoadSetClicked(self):
        self.lastSetSelected = None
        TSHTournamentDataProvider.instance.LoadSets(self)

    def LoadStreamSetClicked(self):
        self.lastSetSelected = None
        TSHTournamentDataProvider.instance.LoadStreamSet(
            self, SettingsManager.Get("twitch_username"))

    def LoadStreamSetOptionsClicked(self):
        TSHTournamentDataProvider.instance.SetTwitchUsername(self)

    def UpdateStreamButton(self):
        if SettingsManager.Get("twitch_username"):
            self.btLoadStreamSet.setText(
                "Load current stream set ("+SettingsManager.Get("twitch_username")+")")
            self.btLoadStreamSet.setEnabled(True)
        else:
            self.btLoadStreamSet.setText("Load current stream set")
            self.btLoadStreamSet.setEnabled(False)

    def UpdateUserSetButton(self):
        provider = None
        if TSHTournamentDataProvider.instance.provider:
            provider = TSHTournamentDataProvider.instance.provider.name
        if provider and SettingsManager.Get(provider+"_user"):
            self.btLoadPlayerSet.setText(
                f"Load user set ({SettingsManager.Get(provider+'_user')})")
            self.btLoadPlayerSet.setEnabled(True)
        else:
            self.btLoadPlayerSet.setText("Load user set")
            self.btLoadPlayerSet.setEnabled(False)

    def LoadUserSetClicked(self):
        self.lastSetSelected = None
        provider = None
        if TSHTournamentDataProvider.instance.provider:
            provider = TSHTournamentDataProvider.instance.provider.name
        if provider and SettingsManager.Get(provider+"_user"):
            TSHTournamentDataProvider.instance.LoadUserSet(
                self, SettingsManager.Get(provider+"_user"))

    def LoadUserSetOptionsClicked(self):
        TSHTournamentDataProvider.instance.SetUserAccount(self)

    def ClearScore(self):
        for c in self.scoreColumn.findChildren(QComboBox):
            c.setCurrentText("")

        for c in self.scoreColumn.findChildren(QSpinBox):
            c.setValue(0)

        self.team1column.findChild(QCheckBox, "losers").setChecked(False)
        self.team2column.findChild(QCheckBox, "losers").setChecked(False)

    def UpdateSetData(self, data):
        print(data)

        if data.get("round_name"):
            self.scoreColumn.findChild(
                QComboBox, "match").setCurrentText(data.get("round_name"))

        if data.get("tournament_phase"):
            self.scoreColumn.findChild(
                QComboBox, "phase").setCurrentText(data.get("tournament_phase"))

        scoreContainers = [
            self.scoreColumn.findChild(QSpinBox, "score_left"),
            self.scoreColumn.findChild(QSpinBox, "score_right")
        ]
        if self.teamsSwapped:
            scoreContainers.reverse()

        if data.get("team1score"):
            scoreContainers[0].setValue(data.get("team1score"))
        if data.get("team2score"):
            scoreContainers[1].setValue(data.get("team2score"))
        if data.get("bestOf"):
            self.scoreColumn.findChild(
                QSpinBox, "best_of").setValue(data.get("bestOf"))

        losersContainers = [
            self.team1column.findChild(QCheckBox, "losers"),
            self.team2column.findChild(QCheckBox, "losers")
        ]
        if self.teamsSwapped:
            losersContainers.reverse()

        if data.get("team1losers") is not None:
            losersContainers[0].setChecked(data.get("team1losers"))
        if data.get("team2losers") is not None:
            losersContainers[1].setChecked(data.get("team2losers"))

        if data.get("entrants"):
            self.playerNumber.setValue(
                len(max(data.get("entrants"), key=lambda x: len(x))))

            for t, team in enumerate(data.get("entrants")):
                teamInstances = [self.team1playerWidgets,
                                 self.team2playerWidgets]
                if self.teamsSwapped:
                    teamInstances.reverse()
                teamInstance = teamInstances[t]

                if len(team) > 1:
                    teamColumns = [self.team1column, self.team2column]
                    teamNames = [data.get("p1_name"), data.get("p2_name")]
                    teamColumns[t].findChild(
                        QLineEdit, "teamName").setText(teamNames[t])

                for p, player in enumerate(team):
                    if data.get("overwrite"):
                        teamInstance[p].SetData(
                            player, False, True)

                    if data.get("has_selection_data"):
                        player = {
                            "mains": player.get("mains")
                        }
                        teamInstance[p].SetData(
                            player, True, False)

        if data.get("stage_strike"):
            StateManager.Set(f"score.stage_strike", data.get("stage_strike"))
