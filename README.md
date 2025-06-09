# PyFback - 期货回测系统

一个高性能的Python期货量化交易回测框架，支持多频率数据回测、策略开发和绩效分析。

## 🚀 特性

- **高性能计算**: 使用Polars、Numba等高性能库加速数据处理和计算
- **多频率支持**: 支持1分钟到日线的多种频率数据回测
- **模块化设计**: 松耦合架构，便于扩展和维护
- **交互式可视化**: 基于Plotly的现代化交互图表
- **完整分析体系**: 从数据加载到报告输出的全流程覆盖
- **灵活策略接口**: 支持多种策略开发模式

## 📁 项目结构

```
pyfback/
├── data/           # 数据模块 - 历史数据加载和缓存
├── strategy/       # 策略模块 - 交易策略定义和信号生成
├── engine/         # 回测引擎 - 核心回测逻辑和交易执行
├── stats/          # 统计分析 - 绩效指标计算和可视化
├── report/         # 报告输出 - HTML/PDF报告和Excel导出
├── examples/       # 使用示例
├── tests/          # 单元测试
└── docs/           # 项目文档
```

## 🛠️ 安装

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/pyfback.git
cd pyfback
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 开发安装
```bash
pip install -e .
```

## 📖 快速开始

### 基本使用示例

```python
import datetime as dt
from data import DataHandler
from strategy.examples import MovingAverageStrategy
from engine import BacktestEngine
from stats import MetricsCalculator
from report import ReportGenerator

# 1. 初始化组件
data_handler = DataHandler()
strategy = MovingAverageStrategy(fast_period=5, slow_period=20)
engine = BacktestEngine(
    data_handler=data_handler,
    strategy=strategy,
    initial_capital=1000000,
    commission=0.0001,
    slippage=0.0001
)

# 2. 运行回测
result = engine.run(
    symbol='IH2312',
    start_date=dt.datetime(2023, 1, 1),
    end_date=dt.datetime(2023, 12, 31),
    freq='1min'
)

# 3. 计算绩效指标
metrics = MetricsCalculator.calculate_all_metrics(result)
print(f"年化收益率: {metrics['annual_return']:.2%}")
print(f"最大回撤: {metrics['max_drawdown']:.2%}")
print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")

# 4. 生成报告
report_generator = ReportGenerator()
report_generator.generate_html(result, 'backtest_report.html')
report_generator.export_excel(result, 'backtest_details.xlsx')
```

### 自定义策略示例

```python
from strategy import StrategyBase, Signal
from data import Bar

class MyStrategy(StrategyBase):
    def __init__(self, period=20):
        super().__init__("我的策略")
        self.period = period
        self.prices = []
    
    def on_bar(self, bar: Bar) -> Signal:
        self.prices.append(bar.close)
        
        if len(self.prices) < self.period:
            return None
            
        # 简单的均值回归策略
        ma = sum(self.prices[-self.period:]) / self.period
        
        if bar.close > ma * 1.02:  # 价格高于均线2%，做空
            return Signal(bar.symbol, direction=-1, quantity=1)
        elif bar.close < ma * 0.98:  # 价格低于均线2%，做多
            return Signal(bar.symbol, direction=1, quantity=1)
        
        return None
```

## 📊 核心模块

### 数据模块 (data/)
- **DataHandler**: 历史数据加载和管理
- **DataCache**: 高效的数据缓存机制
- **Bar**: K线数据结构定义

### 策略模块 (strategy/)
- **StrategyBase**: 策略基类，定义统一接口
- **Signal**: 交易信号数据结构
- **examples/**: 内置策略示例

### 回测引擎 (engine/)
- **BacktestEngine**: 核心回测引擎
- **Portfolio**: 投资组合管理
- **Trade**: 交易记录管理

### 统计分析 (stats/)
- **MetricsCalculator**: 绩效指标计算
- **Visualizer**: 图表生成和可视化
- **RiskAnalysis**: 风险分析工具

### 报告输出 (report/)
- **ReportGenerator**: 报告生成主类
- **templates/**: HTML报告模板
- **ExcelExporter**: Excel详细报表导出

## 🔧 配置

系统配置位于 [`config.py`](config.py:1) 文件中，包含：

- **数据配置**: 支持的频率、缓存设置等
- **回测配置**: 初始资金、手续费、滑点等
- **性能配置**: Numba加速、并行处理等
- **报告配置**: 图表格式、输出目录等

## 📈 支持的绩效指标

- 年化收益率
- 最大回撤
- 夏普比率
- 卡尔马比率
- 胜率
- 盈亏比
- 平均持仓周期
- 波动率
- VaR风险价值
- 更多指标...

## 🎯 性能优化

- **Polars**: 替代Pandas，提供更高的数据处理性能
- **Numba**: JIT编译关键计算函数，大幅提升执行速度
- **并行处理**: 支持多进程并行回测不同策略或时间段
- **数据缓存**: 智能缓存机制减少重复I/O开销
- **向量化计算**: 充分利用NumPy向量化操作

## 📚 文档

- [设计文档](docs/design.md) - 详细的系统设计说明
- [接口文档](docs/interface.pdf) - API接口设计规范
- [基础框架实施规划](基础框架代码实施规划.md) - 完整的实施方案

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定模块测试
pytest tests/test_engine.py

# 生成测试覆盖率报告
pytest --cov=pyfback tests/
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

感谢以下开源项目的支持：
- [Pandas](https://pandas.pydata.org/) & [Polars](https://www.pola.rs/) - 数据处理
- [NumPy](https://numpy.org/) & [Numba](https://numba.pydata.org/) - 数值计算
- [Matplotlib](https://matplotlib.org/) & [Plotly](https://plotly.com/) - 数据可视化
- [Jinja2](https://jinja.palletsprojects.com/) - 模板引擎

## 📞 联系

如有问题或建议，请通过以下方式联系：
- GitHub Issues: [项目Issues页面](https://github.com/yourusername/pyfback/issues)
- Email: your.email@example.com