#include "mainwindow.h"
#include "./ui_mainwindow.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGroupBox>
#include <QStyle>
#include <QPushButton>
#include <QLabel>
#include <QTimer>
#include <QtCharts>
#include <QLineSeries>
#include <QChart>
#include <QChartView>
#include <QValueAxis>
#include <QInputDialog>
#include <QSettings>
#include <QSpinBox>
#include "RegistryHandler.h" // Adjust if needed

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    // 1) Initialize DirectInput
    initializeDirectInput();

    // 2) Set full default calibration ranges
    xRange = {0, 4095};
    zRange = {0, 4095};
    ryRange = {0, 4095};

    // 3) Build the UI
    setupUI();

    // 4) Start update timer
    updateTimer = new QTimer(this);
    connect(updateTimer, &QTimer::timeout, this, &MainWindow::updateValues);
    updateTimer->start(10);
}

MainWindow::~MainWindow()
{
    updateTimer->stop();
    cleanupDirectInput();
    delete ui;
}

void MainWindow::initializeDirectInput()
{
    HRESULT hr = DirectInput8Create(
        GetModuleHandle(NULL),
        DIRECTINPUT_VERSION,
        IID_IDirectInput8,
        (VOID**)&g_pDI,
        NULL
        );
    if (FAILED(hr)) {
        return;
    }
    initializeDevice();
}

bool MainWindow::initializeDevice()
{
    HRESULT hr = g_pDI->EnumDevices(
        DI8DEVCLASS_GAMECTRL,
        [](LPCDIDEVICEINSTANCE lpddi, LPVOID pvRef) -> BOOL {
            MainWindow* self = static_cast<MainWindow*>(pvRef);
            WORD vid = HIWORD(lpddi->guidProduct.Data1);
            WORD pid = LOWORD(lpddi->guidProduct.Data1);

            // For example, if your device is 0x2735 / 0x1DD2
            if (pid != 0x1DD2 || vid != 0x2735) {
                return DIENUM_CONTINUE;
            }

            HRESULT hr = self->g_pDI->CreateDevice(
                lpddi->guidInstance, &self->g_pDevice, NULL
                );
            if (FAILED(hr)) {
                return DIENUM_CONTINUE;
            }

            hr = self->g_pDevice->SetDataFormat(&c_dfDIJoystick2);
            if (FAILED(hr)) {
                self->g_pDevice->Release();
                self->g_pDevice = nullptr;
                return DIENUM_CONTINUE;
            }

            return DIENUM_STOP;
        },
        this, DIEDFL_ATTACHEDONLY
        );

    if (g_pDevice) {
        g_pDevice->SetCooperativeLevel(
            reinterpret_cast<HWND>(winId()),
            DISCL_BACKGROUND | DISCL_NONEXCLUSIVE
            );
        g_pDevice->Acquire();
        return true;
    }
    return false;
}

void MainWindow::cleanupDirectInput()
{
    if (g_pDevice) {
        g_pDevice->Unacquire();
        g_pDevice->Release();
        g_pDevice = nullptr;
    }
    if (g_pDI) {
        g_pDI->Release();
        g_pDI = nullptr;
    }
}

void MainWindow::setupUI()
{
    loadAxisNames();

    QWidget *centralWidget = new QWidget(this);
    QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);
    mainLayout->setContentsMargins(16, 16, 16, 16);
    mainLayout->setSpacing(16);

    setWindowTitle("Axis Calibration");
    setStyleSheet(R"(
        QMainWindow {
            background-color: #1a1b1e;
        }
        QGroupBox {
            background-color: #25262b;
            border: 1px solid #2c2e33;
            border-radius: 8px;
            margin-top: 0.8em;
            padding: 12px;
            color: #e4e5e7;
        }
        QGroupBox::title {
            color: #e4e5e7;
            font-size: 14px;
            font-weight: bold;
            padding: 0 8px;
        }
        QPushButton {
            background-color: #4c6ef5;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 12px;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #5c7cfa;
        }
        QPushButton:pressed {
            background-color: #4263eb;
        }
        QProgressBar {
            border: none;
            border-radius: 4px;
            background-color: #2c2e33;
            min-height: 24px;
            max-height: 24px;
            margin: 4px 0;
            text-align: center;
            font-weight: bold;
            font-size: 12px;
            color: #ffffff;
        }
        QProgressBar::chunk {
            border-radius: 4px;
        }
        QLabel {
            color: #c1c2c5;
            font-size: 12px;
        }
        QMessageBox {
            background-color: #25262b;
            color: #e4e5e7;
        }
        QMessageBox QLabel {
            color: #e4e5e7;
        }
        QMessageBox QPushButton {
            min-width: 80px;
            min-height: 24px;
        }
        QSpinBox {
            background-color: #373a40;
            border: 1px solid #4a4d54;
            border-radius: 4px;
            color: #e4e5e7;
            padding: 4px;
        }
    )");

    // Header
    QHBoxLayout *headerLayout = new QHBoxLayout;
    QPushButton *resetButton = new QPushButton("Reset Calibration", this);
    connect(resetButton, &QPushButton::clicked, this, &MainWindow::resetCalibration);

    QPushButton *restoreButton = new QPushButton("Restore Defaults", this);
    connect(restoreButton, &QPushButton::clicked, this, &MainWindow::restoreDefaults);

    headerLayout->addWidget(resetButton);
    headerLayout->addSpacing(10);
    headerLayout->addWidget(restoreButton);
    headerLayout->addStretch();
    mainLayout->addLayout(headerLayout);

    // Horizontal layout for axes
    QHBoxLayout *axesLayout = new QHBoxLayout;
    axesLayout->setSpacing(16);

    auto createAxisGroup = [this](
                               QString &axisName,
                               QLabel *&valueLabel,
                               QProgressBar *&rawBar,
                               QProgressBar *&calBar,
                               int axisIndex)
    {
        QGroupBox *group = new QGroupBox();
        QVBoxLayout *layout = new QVBoxLayout;
        layout->setSpacing(8);
        layout->setContentsMargins(12, 12, 12, 12);

        // Title + rename
        QHBoxLayout *titleLayout = new QHBoxLayout;
        QWidget *titleContainer = new QWidget;
        QHBoxLayout *titleTextLayout = new QHBoxLayout(titleContainer);
        titleTextLayout->setSpacing(4);
        titleTextLayout->setContentsMargins(0, 0, 0, 0);

        QLabel *titleLabel = new QLabel(axisName);
        titleLabel->setStyleSheet("font-weight: bold; font-size: 14px; color: #e4e5e7;");

        QPushButton *editButton = new QPushButton("✎");
        editButton->setFixedSize(24, 24);
        editButton->setStyleSheet(R"(
            QPushButton {
                border: none;
                background: transparent;
                color: #6b7280;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #374151;
                color: #e4e5e7;
                border-radius: 4px;
            }
        )");

        titleTextLayout->addWidget(titleLabel);
        titleTextLayout->addWidget(editButton);
        titleTextLayout->addStretch();

        QChartView *chartView = nullptr;
        if (axisIndex == 0) {
            chartView = createAxisChart("X-Axis History", xSeries);
            xChartView = chartView;
        } else if (axisIndex == 1) {
            chartView = createAxisChart("Z-Axis History", zSeries);
            zChartView = chartView;
        } else {
            chartView = createAxisChart("RY-Axis History", rySeries);
            ryChartView = chartView;
        }
        layout->addWidget(chartView);

        titleLayout->addWidget(titleContainer);
        layout->addLayout(titleLayout);

        // Renaming axis
        connect(editButton, &QPushButton::clicked, this, [=, &axisName]() {
            bool ok;
            QString newName = QInputDialog::getText(
                this, "Rename Axis",
                "Enter new axis name:",
                QLineEdit::Normal,
                axisName, &ok
                );
            if (ok && !newName.isEmpty()) {
                axisName = newName;
                titleLabel->setText(newName);

                QSettings settings("SimCoaches", "TrackPro");
                settings.beginGroup("AxisNames");
                if (axisIndex == 0) settings.setValue("X", newName);
                else if (axisIndex == 1) settings.setValue("Z", newName);
                else if (axisIndex == 2) settings.setValue("RY", newName);
                settings.endGroup();
            }
        });

        // Value display
        QHBoxLayout *valueLayout = new QHBoxLayout;
        QLabel *valueTitle = new QLabel("Current Value:");
        valueLabel = new QLabel("0");
        valueLabel->setStyleSheet("font-weight: bold; color: #e4e5e7; font-size: 14px;");
        valueLayout->addWidget(valueTitle);
        valueLayout->addWidget(valueLabel);
        valueLayout->addStretch();
        layout->addLayout(valueLayout);

        // Progress bars
        QLabel *rawLabel = new QLabel("Raw Input");
        rawBar = new QProgressBar;
        rawBar->setTextVisible(true);
        rawBar->setStyleSheet("QProgressBar::chunk { background-color: #fd7e14; }");

        QLabel *calLabel = new QLabel("Calibrated");
        calBar = new QProgressBar;
        calBar->setTextVisible(true);
        calBar->setStyleSheet("QProgressBar::chunk { background-color: #228be6; }");

        layout->addWidget(rawLabel);
        layout->addWidget(rawBar);
        layout->addWidget(calLabel);
        layout->addWidget(calBar);

        // Buttons min/max
        QHBoxLayout *buttonLayout = new QHBoxLayout;
        buttonLayout->setSpacing(8);
        QPushButton *minButton = new QPushButton("Set Minimum");
        QPushButton *maxButton = new QPushButton("Set Maximum");
        minButton->setFixedHeight(32);
        maxButton->setFixedHeight(32);

        connect(minButton, &QPushButton::clicked, this, [this, axisIndex]() {
            setAxisMin(axisIndex);
        });
        connect(maxButton, &QPushButton::clicked, this, [this, axisIndex]() {
            setAxisMax(axisIndex);
        });

        buttonLayout->addWidget(minButton);
        buttonLayout->addWidget(maxButton);
        layout->addLayout(buttonLayout);

        // Deadzones
        QGroupBox* deadzoneGroup = new QGroupBox("Deadzones");
        deadzoneGroup->setStyleSheet(R"(
            QGroupBox {
                margin-top: 16px;
                padding-top: 16px;
                background-color: #2c2e33;
            }
        )");
        QGridLayout* deadzoneLayout = new QGridLayout(deadzoneGroup);
        deadzoneLayout->setSpacing(8);

        QSpinBox* minDeadzoneSpinner = new QSpinBox();
        minDeadzoneSpinner->setRange(0, 20);
        minDeadzoneSpinner->setSuffix("%");

        QSpinBox* maxDeadzoneSpinner = new QSpinBox();
        maxDeadzoneSpinner->setRange(0, 20);
        maxDeadzoneSpinner->setSuffix("%");

        deadzoneLayout->addWidget(minDeadzoneSpinner, 0, 1);
        deadzoneLayout->addWidget(maxDeadzoneSpinner, 1, 1);

        QLabel* minDeadzoneLabel = new QLabel("Min Deadzone:");
        QLabel* maxDeadzoneLabel = new QLabel("Max Deadzone:");
        deadzoneLayout->addWidget(minDeadzoneLabel, 0, 0);
        deadzoneLayout->addWidget(maxDeadzoneLabel, 1, 0);

        connect(minDeadzoneSpinner, QOverload<int>::of(&QSpinBox::valueChanged),
                this, [this, axisIndex](int value) {
                    std::wstring calibrationData;
                    switch(axisIndex) {
                    case 0:
                        calibrationData = L"MinX=" + std::to_wstring(xRange.min) +
                                          L";MaxX=" + std::to_wstring(xRange.max) +
                                          L";MinDeadzoneX=" + std::to_wstring(value) + L";";
                        break;
                    case 1:
                        calibrationData = L"MinZ=" + std::to_wstring(zRange.min) +
                                          L";MaxZ=" + std::to_wstring(zRange.max) +
                                          L";MinDeadzoneZ=" + std::to_wstring(value) + L";";
                        break;
                    case 2:
                        calibrationData = L"MinRY=" + std::to_wstring(ryRange.min) +
                                          L";MaxRY=" + std::to_wstring(ryRange.max) +
                                          L";MinDeadzoneRY=" + std::to_wstring(value) + L";";
                        break;
                    }
                    saveCalibrationToRegistry(calibrationData, axisIndex);
                });

        connect(maxDeadzoneSpinner, QOverload<int>::of(&QSpinBox::valueChanged),
                this, [this, axisIndex](int value) {
                    std::wstring calibrationData;
                    switch(axisIndex) {
                    case 0:
                        calibrationData = L"MinX=" + std::to_wstring(xRange.min) +
                                          L";MaxX=" + std::to_wstring(xRange.max) +
                                          L";MaxDeadzoneX=" + std::to_wstring(value) + L";";
                        break;
                    case 1:
                        calibrationData = L"MinZ=" + std::to_wstring(zRange.min) +
                                          L";MaxZ=" + std::to_wstring(zRange.max) +
                                          L";MaxDeadzoneZ=" + std::to_wstring(value) + L";";
                        break;
                    case 2:
                        calibrationData = L"MinRY=" + std::to_wstring(ryRange.min) +
                                          L";MaxRY=" + std::to_wstring(ryRange.max) +
                                          L";MaxDeadzoneRY=" + std::to_wstring(value) + L";";
                        break;
                    }
                    saveCalibrationToRegistry(calibrationData, axisIndex);
                });

        layout->addWidget(deadzoneGroup);
        layout->addStretch();
        group->setLayout(layout);
        return group;
    };

    axesLayout->addWidget(createAxisGroup(xAxisName, xValueLabel, xRawBar, xCalBar, 0));
    axesLayout->addWidget(createAxisGroup(zAxisName, zValueLabel, zRawBar, zCalBar, 1));
    axesLayout->addWidget(createAxisGroup(ryAxisName, ryValueLabel, ryRawBar, ryCalBar, 2));

    mainLayout->addLayout(axesLayout);
    mainLayout->addStretch();

    setCentralWidget(centralWidget);
    resize(1000, 600); // Make the window bigger
}

QChartView* MainWindow::createAxisChart(const QString &title, QLineSeries*& series)
{
    QChart *chart = new QChart();
    chart->legend()->hide();

    // Try giving some margins so labels have room
    chart->setMargins(QMargins(10, 10, 10, 10));
    chart->setBackgroundBrush(QBrush(QColor("#25262b")));

    QValueAxis *axisX = new QValueAxis();
    axisX->setRange(0, GRAPH_HISTORY);
    axisX->setLabelsVisible(false); // hide horizontal labels
    axisX->setLabelsColor(QColor("#c1c2c5"));

    QValueAxis *axisY = new QValueAxis();
    axisY->setRange(0, 4095);
    axisY->setTickCount(5);          // e.g. 0, ~1000, ~2000, ~3000, ~4095
    axisY->setLabelFormat("%.0f");   // integer labels, no decimals
    axisY->setLabelsVisible(true);   // ensure they're visible
    axisY->setLabelsColor(QColor("#c1c2c5"));
    axisY->setGridLineColor(QColor("#373a40"));

    series = new QLineSeries();
    QPen seriesPen(QColor("#4c6ef5"));
    seriesPen.setWidth(2);
    series->setPen(seriesPen);

    chart->addSeries(series);
    chart->addAxis(axisX, Qt::AlignBottom);
    chart->addAxis(axisY, Qt::AlignLeft);
    series->attachAxis(axisX);
    series->attachAxis(axisY);

    // Make the chart a bit taller so labels fit
    QChartView *chartView = new QChartView(chart);
    chartView->setRenderHint(QPainter::Antialiasing);
    chartView->setFixedHeight(150);
    chartView->setBackgroundBrush(QBrush(QColor("#1a1b1e")));

    return chartView;
}

void MainWindow::updateValues()
{
    if (!g_pDevice) return;

    DIJOYSTATE2 js;
    HRESULT hr = g_pDevice->Poll();
    if (FAILED(hr)) {
        g_pDevice->Acquire();
        hr = g_pDevice->Poll();
    }

    if (SUCCEEDED(hr) && SUCCEEDED(g_pDevice->GetDeviceState(sizeof(DIJOYSTATE2), &js))) {
        // 1) Convert to 0..4095
        currentXRaw  = static_cast<LONG>(js.lX  * (4095.0 / 65535.0));
        currentZRaw  = static_cast<LONG>(js.lZ  * (4095.0 / 65535.0));
        currentRYRaw = static_cast<LONG>(js.lRy * (4095.0 / 65535.0));

        // 2) If calibrated, scale to 0..100
        double xScaled  = (double(currentXRaw  - xRange.min) / (xRange.max - xRange.min)) * 100.0;
        double zScaled  = (double(currentZRaw  - zRange.min) / (zRange.max - zRange.min)) * 100.0;
        double ryScaled = (double(currentRYRaw - ryRange.min) / (ryRange.max - ryRange.min)) * 100.0;

        auto clamp01 = [](double v){ return std::max(0.0, std::min(100.0, v)); };
        xScaled = clamp01(xScaled);
        zScaled = clamp01(zScaled);
        ryScaled= clamp01(ryScaled);

        // 3) Plot either raw or scaled
        double xForChart  = (m_calibrated ? xScaled  : currentXRaw);
        double zForChart  = (m_calibrated ? zScaled  : currentZRaw);
        double ryForChart = (m_calibrated ? ryScaled : currentRYRaw);

        xHistory.push_back(xForChart);
        if (xHistory.size() > GRAPH_HISTORY) xHistory.pop_front();
        zHistory.push_back(zForChart);
        if (zHistory.size() > GRAPH_HISTORY) zHistory.pop_front();
        ryHistory.push_back(ryForChart);
        if (ryHistory.size() > GRAPH_HISTORY) ryHistory.pop_front();

        xSeries->clear();
        for (int i = 0; i < (int)xHistory.size(); ++i) {
            xSeries->append(i, xHistory[i]);
        }
        zSeries->clear();
        for (int i = 0; i < (int)zHistory.size(); ++i) {
            zSeries->append(i, zHistory[i]);
        }
        rySeries->clear();
        for (int i = 0; i < (int)ryHistory.size(); ++i) {
            rySeries->append(i, ryHistory[i]);
        }

        // 4) Adjust Y-range + tick count
        QValueAxis* xAxisY = qobject_cast<QValueAxis*>(xChartView->chart()->axes(Qt::Vertical).first());
        QValueAxis* zAxisY = qobject_cast<QValueAxis*>(zChartView->chart()->axes(Qt::Vertical).first());
        QValueAxis* ryAxisY= qobject_cast<QValueAxis*>(ryChartView->chart()->axes(Qt::Vertical).first());

        if (m_calibrated) {
            xAxisY->setRange(0, 100);
            xAxisY->setTickCount(6);       // 0,20,40,60,80,100
            xAxisY->setLabelFormat("%.0f");

            zAxisY->setRange(0, 100);
            zAxisY->setTickCount(6);
            zAxisY->setLabelFormat("%.0f");

            ryAxisY->setRange(0, 100);
            ryAxisY->setTickCount(6);
            ryAxisY->setLabelFormat("%.0f");
        } else {
            xAxisY->setRange(0, 4095);
            xAxisY->setTickCount(5);       // e.g. 0..4095 in 5 steps
            xAxisY->setLabelFormat("%.0f");

            zAxisY->setRange(0, 4095);
            zAxisY->setTickCount(5);

            ryAxisY->setRange(0, 4095);
            ryAxisY->setTickCount(5);
        }

        // 5) Update progress bars & label
        auto updateAxis = [](QLabel *label, QProgressBar *rawBar, QProgressBar *calBar,
                             LONG raw, const AxisRange &range)
        {
            int rawPercent = (raw * 100) / 4095;
            int calPercent = 0;
            if (raw <= range.min) {
                calPercent = 0;
            } else if (raw >= range.max) {
                calPercent = 100;
            } else {
                calPercent = ((raw - range.min) * 100) / (range.max - range.min);
            }

            label->setText(QString("%1 (%2%)").arg(raw).arg(rawPercent));
            rawBar->setValue(rawPercent);
            rawBar->setFormat(QString("%1%").arg(rawPercent));
            calBar->setValue(calPercent);
            calBar->setFormat(QString("%1%").arg(calPercent));
        };

        updateAxis(xValueLabel, xRawBar, xCalBar, currentXRaw, xRange);
        updateAxis(zValueLabel, zRawBar, zCalBar, currentZRaw, zRange);
        updateAxis(ryValueLabel, ryRawBar, ryCalBar, currentRYRaw, ryRange);
    }
}

void MainWindow::resetCalibration()
{
    // Back to raw
    m_calibrated = false;

    xRange = {0, 4095};
    zRange = {0, 4095};
    ryRange = {0, 4095};

    std::wstring xCalibration = L"MinX=0;MaxX=4095;";
    std::wstring zCalibration = L"MinZ=0;MaxZ=4095;";
    std::wstring ryCalibration = L"MinRY=0;MaxRY=4095;";

    saveCalibrationToRegistry(xCalibration, 0);
    saveCalibrationToRegistry(zCalibration, 1);
    saveCalibrationToRegistry(ryCalibration, 2);
}

void MainWindow::restoreDefaults()
{
    backupCurrentCalibration();

    m_calibrated = false;
    xRange = {0, 4095};
    zRange = {0, 4095};
    ryRange = {0, 4095};

    std::wstring xCalibration = L"MinX=0;MaxX=4095;";
    std::wstring zCalibration = L"MinZ=0;MaxZ=4095;";
    std::wstring ryCalibration = L"MinRY=0;MaxRY=4095;";

    saveCalibrationToRegistry(xCalibration, 0);
    saveCalibrationToRegistry(zCalibration, 1);
    saveCalibrationToRegistry(ryCalibration, 2);

    QMessageBox::information(this, "Restore Defaults",
                             "All axes have been reset to factory defaults.\n"
                             "You can use 'Restore Last Calibration' to undo this action.");
}

void MainWindow::loadAxisNames()
{
    QSettings settings("SimCoaches", "TrackPro");
    settings.beginGroup("AxisNames");
    xAxisName = settings.value("X", "X-Axis").toString();
    zAxisName = settings.value("Z", "Z-Axis").toString();
    ryAxisName = settings.value("RY", "RY-Axis").toString();
    settings.endGroup();
}

void MainWindow::saveAxisNames()
{
    QSettings settings("SimCoaches", "TrackPro");
    settings.beginGroup("AxisNames");
    settings.setValue("X", xAxisName);
    settings.setValue("Z", zAxisName);
    settings.setValue("RY", ryAxisName);
    settings.endGroup();
}

bool MainWindow::validateAxisRange(const AxisRange& range, const QString& axisName)
{
    if (range.min >= range.max) {
        QMessageBox::warning(this, "Invalid Range",
                             QString("%1: Minimum value (%2) must be less than maximum value (%3)")
                                 .arg(axisName)
                                 .arg(range.min)
                                 .arg(range.max));
        return false;
    }
    if ((range.max - range.min) < 409) {
        QMessageBox::warning(this, "Small Range",
                             QString("%1: The calibration range seems very small. This might affect precision.")
                                 .arg(axisName));
        return false;
    }
    return true;
}

bool MainWindow::isValueUnusual(LONG value, const QString& axisName)
{
    if (value < 100 || value > 3995) {
        QMessageBox::warning(this, "Unusual Value",
                             QString("%1: The value %2 is very close to the extreme. Please verify your input.")
                                 .arg(axisName)
                                 .arg(value));
        return true;
    }
    return false;
}

void MainWindow::backupCurrentCalibration()
{
    CalibrationBackup backup = { xRange, zRange, ryRange };
    calibrationHistory.push_back(backup);

    if (calibrationHistory.size() > 10) {
        calibrationHistory.erase(calibrationHistory.begin());
    }
}

void MainWindow::restoreLastCalibration()
{
    if (calibrationHistory.empty()) {
        QMessageBox::information(this, "Restore", "No previous calibration available");
        return;
    }

    auto backup = calibrationHistory.back();
    xRange = backup.x;
    zRange = backup.z;
    ryRange = backup.ry;
    calibrationHistory.pop_back();

    std::wstring xCalibration = L"MinX=" + std::to_wstring(xRange.min) + L";MaxX=" + std::to_wstring(xRange.max) + L";";
    std::wstring zCalibration = L"MinZ=" + std::to_wstring(zRange.min) + L";MaxZ=" + std::to_wstring(zRange.max) + L";";
    std::wstring ryCalibration = L"MinRY=" + std::to_wstring(ryRange.min) + L";MaxRY=" + std::to_wstring(ryRange.max) + L";";

    saveCalibrationToRegistry(xCalibration, 0);
    saveCalibrationToRegistry(zCalibration, 1);
    saveCalibrationToRegistry(ryCalibration, 2);

    QMessageBox::information(this, "Restore", "Previous calibration restored successfully");
}

void MainWindow::setAxisMin(int axis)
{
    std::wstring calibrationData;
    switch (axis) {
    case 0:
        xRange.min = currentXRaw;
        calibrationData = L"MinX=" + std::to_wstring(xRange.min) +
                          L";MaxX=" + std::to_wstring(xRange.max) + L";";
        saveCalibrationToRegistry(calibrationData, 0);
        break;
    case 1:
        zRange.min = currentZRaw;
        calibrationData = L"MinZ=" + std::to_wstring(zRange.min) +
                          L";MaxZ=" + std::to_wstring(zRange.max) + L";";
        saveCalibrationToRegistry(calibrationData, 1);
        break;
    case 2:
        ryRange.min = currentRYRaw;
        calibrationData = L"MinRY=" + std::to_wstring(ryRange.min) +
                          L";MaxRY=" + std::to_wstring(ryRange.max) + L";";
        saveCalibrationToRegistry(calibrationData, 2);
        break;
    }
}

void MainWindow::setAxisMax(int axis)
{
    std::wstring calibrationData;
    switch (axis) {
    case 0:
        xRange.max = currentXRaw;
        calibrationData = L"MinX=" + std::to_wstring(xRange.min) +
                          L";MaxX=" + std::to_wstring(xRange.max) + L";";
        saveCalibrationToRegistry(calibrationData, 0);

        // Here we switch to calibrated mode once X is set
        m_calibrated = true;
        break;
    case 1:
        zRange.max = currentZRaw;
        calibrationData = L"MinZ=" + std::to_wstring(zRange.min) +
                          L";MaxZ=" + std::to_wstring(zRange.max) + L";";
        saveCalibrationToRegistry(calibrationData, 1);

        m_calibrated = true;
        break;
    case 2:
        ryRange.max = currentRYRaw;
        calibrationData = L"MinRY=" + std::to_wstring(ryRange.min) +
                          L";MaxRY=" + std::to_wstring(ryRange.max) + L";";
        saveCalibrationToRegistry(calibrationData, 2);

        m_calibrated = true;
        break;
    }
}

void MainWindow::adjustDeadzone(int axis, bool isTop, bool increase, QLabel* valueLabel)
{
    DeadzoneSettings* deadzone = nullptr;
    if (axis == 0) deadzone = &xDeadzone;
    else if (axis == 1) deadzone = &zDeadzone;
    else if (axis == 2) deadzone = &ryDeadzone;

    if (!deadzone) {
        qDebug() << "Invalid axis index:" << axis;
        return;
    }

    LONG* targetDeadzone = isTop ? &deadzone->maxDeadzone : &deadzone->minDeadzone;
    if (!targetDeadzone) {
        qDebug() << "Invalid deadzone pointer.";
        return;
    }

    if (increase && *targetDeadzone < 20) {
        ++(*targetDeadzone);
    } else if (!increase && *targetDeadzone > 0) {
        --(*targetDeadzone);
    } else {
        qDebug() << "Deadzone adjustment out of range or no change.";
        return;
    }

    *targetDeadzone = std::clamp(*targetDeadzone, 0L, 20L);

    if (valueLabel) {
        valueLabel->setText(QString::number(*targetDeadzone) + "%");
    }
}

void MainWindow::saveDeadzoneSettings(int axis)
{
    std::wstring calibrationData;
    DeadzoneSettings* deadzone = nullptr;

    if (axis == 0) {
        deadzone = &xDeadzone;
        calibrationData = L"MinDeadzoneX=" + std::to_wstring(deadzone->minDeadzone) +
                          L";MaxDeadzoneX=" + std::to_wstring(deadzone->maxDeadzone) + L";";
    } else if (axis == 1) {
        deadzone = &zDeadzone;
        calibrationData = L"MinDeadzoneZ=" + std::to_wstring(deadzone->minDeadzone) +
                          L";MaxDeadzoneZ=" + std::to_wstring(deadzone->maxDeadzone) + L";";
    } else if (axis == 2) {
        deadzone = &ryDeadzone;
        calibrationData = L"MinDeadzoneRY=" + std::to_wstring(deadzone->minDeadzone) +
                          L";MaxDeadzoneRY=" + std::to_wstring(deadzone->maxDeadzone) + L";";
    }

    saveCalibrationToRegistry(calibrationData, axis);
}

void MainWindow::updateDeadzoneVisuals()
{
    // optional
}
