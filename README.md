# ExtractChinese
提取代码里中文字符
启动项：
all： 给出一个路径，比如：D:\project\Assets\Scripts\Game\Module\Function 则扫描此目录下所有文件夹，每个文件夹对应一个，生成一个csv，csv的名字就是文件夹名字，生成的csv都在根目录Function下，
single： 给出一个路径，比如：D:\project\Assets\Scripts\Game\Module\Function\Battle  则只扫描本目录下所有代码，只生成一个csv，放在跟Battle同层级

规则：
1.定位到给出的目录下，递归遍历所有代码
1.找到代码中使用中文的地方做一个记录，每个目标文件夹输出一个文件，忽略注释中的中文   以Draw为例：输出一个csv文件 命名为draw  表头为key  value  pos  
3.key规则：key不允许有中文  以文件夹名字开头，根据提取出的中文，翻译生成一个描述具体含义的变量名字，格式为 DRAW_NEW_POOL_TIME_LIMIT 比如GService.Prompt.ShowPrompt($"抽卡道具不足"); 得到 DRAW_DRAW_ITEM_INSUFFICIENT
4.value规则：
如果是没有参数的string，比如$"抽卡道具不足"  则value为：抽卡道具不足  
如果有参数，比如$"再结义 {leftNum} 次必得红将" 则value为 再结义 {0} 次必得红将   $"累计抽取{cfg.reward_times}次（{totalCount}/{cfg.reward_times}）";则value为 累计抽取{0}次（{1}/{2}）
5.pos规则：xx.cs--- 行数

注意事项：
注意：扫描代码时，如果文件夹以Bind为名字，或者以Bind为结尾，则跳过这个文件或文件夹
注意：忽略注释，忽略一些log相关的api，比如Unity自带的Api，Debug.Log、Debug.LogError  项目中SLApp.Debug类的所有方法
注意：$"再结义 {leftNum} 次必得红将";  期望得到的格式是  再结义 {0} 次必得红将    $""是c#的语法，中间的{}是要匹配的参数
注意：忽略Attribute声明中的中文 比如  [Header("Timeline资源 (从Playable Director拖入)")] 直接无视
注意：忽略region  #region 拖拽  #endregion  拖拽需要跳过   但是region的代码段还是要扫描
注意：忽略文件头部注释中的中文，比如
/** Author: GuoZheng
* Date: 2026.01.28 11:16
 * Description: 每个抽卡池的数据类
 */
