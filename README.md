# TempChamberRemoteController
This is a GUI tool running on Windosws OS for remote controlling temperature chamber which produced by “重庆银河试验”.

This GUI could connect with chamber/read current running status/read current temperature/set target temperature.

Most importantly, this GUI could set a wave on plot and make chamber's temperature follow the wave.

This tool only works with chamber produced by “重庆银河试验仪器有限公司”, and the software communication protocol may change, which could cause the function to fail. 

Therefore, it is necessary to confirm before using it.


ChamCtrl.exe是一个可以单独运行的GUI软件，用python编写和打包。作者为吴宪，反馈邮箱为xian.wu@ericsson.com或dakongwuxian@gmail.com。

该软件的功能有：
连接内网指定IP的温箱，获取当前的状态、温度，设置温箱的温度，指定（时间-温度）坐标的折线图，预览折线图，保存折线图设定，让温箱以折线图的指定值变温运行。

如果温箱的IP地址发生了变化，也可以手动输入IP地址。

点击connect按键后，可以看到状态变为run/pause/stop，并显示当前温箱温度温度。

通过手动操作面板的方式，先让温箱进入恒温运行状态，保持软件为connect状态，即可通过Set按键，将Target temp中的温度值发送给温箱，温箱即会以此为设定值开始运行。

界面上方的绘图区会显示获取到的（时间，温度）点，并保存在ChamCtrlLog.txt中，每次更新绘图区域时，会将当前log文件中的所有点绘制上去。

如果ChamCtrlLog.txt文件超过10M，软件会将当前的文件关闭并另存为

横坐标有2个，上方的横坐标为日期，下方的横坐标为时间。

点击x y轴对应的4个按键，可以缩放和移动坐标轴。

在绘图区域滚动鼠标滚轮，也可以实现横坐标的缩放。

在绘图区域点击左键，会让附近最近的点被圈中显示，并显示其（时间-温度）值。

点击 current to center，会将横轴移动到以当前时间点为中心的位置。

Auto Center如果勾选，每次有新的温度点绘制后，会将其移动到屏幕中心。

Auto Mark如果勾选，每次有新的温度点绘制后，会将其圈起来并显示其坐标。

启动后，temp wave setting文本框默认为空，点击load wave会选择txt文件并加载文件的文本到文本框中。

编写了3个可加载并运行的示例，文件名为：
“temp loop setting_start at 25_80C 60 min_-40C 60min_10 times.txt“
“temp loop setting_start at -40_-40C 60 min_80C 60min_3 times.txt”
“temp loop setting_start at 80_80C 60 min_-40C 60min_5 times.txt”
文件内容为：
(start temp 25C)-(loop count 10)-[(0,25C)-(55,80C)-(60,80C)-(120,-40C)-(60,-40C)-(65,25C)]
(start temp -40C)-(loop count 3)-[(0,-40C)-(60,-40C)-(120,80C)-(60,80C)-(120,-40C)]
(start temp 80C)-(loop count 5)-[(0,80C)-(60,80C)-(120,-40C)-(60,-40C)-(120,80C)]

加载文件后，文本框中出现字符串，点击wave preview，则可以看到该（时间-温度）折线图的预览效果。

通过手动操作面板的方式，先让温箱进入恒温运行状态，保持软件为connect状态，保持多行文本框中有正确格式的字符串，点击Wave Start按键，软件便会开始操控温箱变温运行，直到设定的折线运行完。

变温运行状态中，再次点击按键，即会提前结束运行。

多行文本框中的内容，点击Save Wave，即会弹出窗口进行另存为操作。

折线图对应字符串的格式说明：
(start temp 25C)-(loop count 10)-[(0,25C)-(55,80C)-(60,80C)-(120,-40C)-(60,-40C)-(65,25C)]
以上面这一行为例，
start temp 25C表示以25摄氏度作为起始温度，如果当前温箱的温度为90摄氏度，则会先让温箱以1℃/min的速率先运行到25度，然后再执行后续的温度设定；
loop count 10，表示后面的中括号中的内容会循环10次；
(0,25C)-(55,80C)-……，表示的是（时间，温度）的坐标点，温度循环曲线要求起始温度和结束温度要相同，否则会出现温度变化斜率过高，温箱实际运行出现跟预期不符的情况。

对于温度保持不变的2个点，软件不会多次对温箱发送命令，仅会在线段的起点发送一次命令；
对于温度有变化的2个点，软件会先以每分钟进行分隔和插值，然后每分钟发送一次命令给温箱。

当前的设置方式，不能完全保证温箱运行的温变速率，1℃/min是建议的温变速率。
如果你设定的温度斜率过高，软件也不会进行报警。
