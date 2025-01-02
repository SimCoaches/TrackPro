#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QLabel>
#include <QProgressBar>
#include <QTimer>
#include <dinput.h>
#include <QtCharts>
#include <deque>
#include <QMessageBox>

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

    // Axis structures
    struct AxisRange {
        LONG min;
        LONG max;
    };

private slots:
    void updateValues();
    void resetCalibration();
    void restoreDefaults();
    void setAxisMin(int axis);
    void setAxisMax(int axis);

private:
    Ui::MainWindow *ui;

    // DirectInput
    LPDIRECTINPUT8 g_pDI = nullptr;
    LPDIRECTINPUTDEVICE8 g_pDevice = nullptr;
    void initializeDirectInput();
    bool initializeDevice();
    void cleanupDirectInput();

    // Are we showing calibrated 0..100 instead of raw 0..4095?
    bool m_calibrated = false;

    // Chart members
    static const int GRAPH_HISTORY = 100;
    QLineSeries *xSeries = nullptr;
    QLineSeries *zSeries = nullptr;
    QLineSeries *rySeries = nullptr;
    QChartView *xChartView = nullptr;
    QChartView *zChartView = nullptr;
    QChartView *ryChartView = nullptr;

    // Data histories
    std::deque<double> xHistory;
    std::deque<double> zHistory;
    std::deque<double> ryHistory;

    // Chart creation
    QChartView* createAxisChart(const QString &title, QLineSeries*& series);

    // Axis names
    QString xAxisName;
    QString zAxisName;
    QString ryAxisName;
    void saveAxisNames();
    void loadAxisNames();

    // UI elements
    QLabel *xValueLabel = nullptr;
    QLabel *zValueLabel = nullptr;
    QLabel *ryValueLabel = nullptr;
    QProgressBar *xRawBar = nullptr;
    QProgressBar *xCalBar = nullptr;
    QProgressBar *zRawBar = nullptr;
    QProgressBar *zCalBar = nullptr;
    QProgressBar *ryRawBar = nullptr;
    QProgressBar *ryCalBar = nullptr;
    QTimer *updateTimer = nullptr;

    // Current raw values
    LONG currentXRaw = 0;
    LONG currentZRaw = 0;
    LONG currentRYRaw = 0;

    // Calibration ranges
    AxisRange xRange;
    AxisRange zRange;
    AxisRange ryRange;

    // Setup UI
    void setupUI();

    // Validation
    bool validateAxisRange(const AxisRange& range, const QString& axisName);
    bool isValueUnusual(LONG value, const QString& axisName);

    // Backup & restore
    struct CalibrationBackup { AxisRange x, z, ry; };
    std::vector<CalibrationBackup> calibrationHistory;
    void backupCurrentCalibration();
    void restoreLastCalibration();
};

#endif // MAINWINDOW_H
