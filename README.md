netlist-checker
===============

EDIF netlist checker tool
bunnie "at" bunniestudios daht com // BSD licensed

This tool is designed to work with Altium Designer netlists. The
netlist should be generated using the menu option Design->Netlist for
Project->EDIF for PCB. It is tested for compatibility with AD10.

This tool requires the Levenshtein and pyparsing modules. You'll probably
have to install Levenshtein in particular.

Also note that for large designs (netlists larger than about 100kB)
initial grammar parsing can take a while, around 30 seconds for 2
megabytes.

The options supported by v0.1 are:

 npn <n> -- print nets with <n> pins
 spn -- report single pin nets only
 cnt -- count and report pins per net
 drc <0.n> -- drc checks with Levenshtein tolerance of <0.n>. Default is 0.1, range is 0-1, with smaller being stricter; recommended values are 0.1 or 0.11
 list <net> -- list components on net <net>
 q -- quit the program
 dbg -- break into the debugger

The drc option is useful for identifying potential typos in netlist entry.

The list option is useful for quickly verifying things such a maximum
voltage rating compatibility of components with certain netlists,
assuming you use the convention of embodying the max voltage rating of
a component in the comment field.

The dbg option is useful for quickly browsing the processed netlist
and component databases with scripts entered in the python interactive
debugger.

Note that the included test1_short.EDF is provided more for checking
parser functionality and it doesn't cover comprehensive test cases.

Here are some examples of the checker in action:

--------------------------------------------------

netlist> drc
single pin nets: 
['NET_ERROR']
Typo candidates: 
Similarly-named nets found: 
[['AUD_MCLK', 'AUD_CLK'],
 ['AUD_MCLK_T', 'AUD_CLK_T'],
 ['CN_L_SPK_LINE', 'CN_R_SPK_LINE'],
 ['CN_R_SPK_LINE', 'CN_L_SPK_LINE'],
 ['DDR3_BA0', 'DDR3_A0'],
 ['DDR3_BA1', 'DDR3_A1'],
 ['DDR3_BA2', 'DDR3_A2'],
 ['EN100_A1.8V', 'EN100_D1.8V'],
 ['EN100_D1.8V', 'EN100_A1.8V'],
 ['EN100_XTL25N', 'EN100_XTL25P'],
 ['EN100_XTL25P', 'EN100_XTL25N'],
 ['PCIE_WWAN_LED', 'PCIE_WLAN_LED'],
 ['PCIE_WWAN_LED', 'PCIE_WPAN_LED'],
 ['RGMII_RXCLK', 'RGMII_TXCLK'],
 ['RGMII_TXCLK', 'RGMII_RXCLK'],
 ['SD2_CMD', 'SD2_CD']]
Orphaned differential net syntax found (there is either a lone _P or _N variant of this net): 
HDMI_HPD_LV

--------------------------------------------------

netlist> cnt
{1: ['NET_ERROR'],
 2: ['ANA_IN0',
     'ANA_IN1',
     'ANA_IN2',
     'ANA_IN3',
     'ANA_IN4',
...
 42: ['P3.3V'],
 43: ['P5.0V_DELAYED'],
 73: ['P1.5V_DDR_SW3'],
 260: ['P3.3V_DELAYED'],
 936: ['GND']}
Number of 1 pin nets: 1
Number of 2 pin nets: 396
Number of 3 pin nets: 170
Number of 4 pin nets: 78
Number of 5 pin nets: 16
Number of 6 pin nets: 5
...
Number of 36 pin nets: 1
Number of 936 pin nets: 1
Number of 42 pin nets: 1
Number of 43 pin nets: 1
Number of 73 pin nets: 1

--------------------------------------------------

netlist> list BATT_PWR
Components attached to net 'BATT_PWR':
C11N: 0.1uF, 25V, X5R
C12N: 1.0uF, 25V, 20% X5R
C14N: 22uF, 25V, X5R, 10%
C15N: 22uF, 25V, X5R, 10%
C16N: 22uF, 25V, X5R, 10% (DNP)
C17N: 22uF, 25V, X5R, 10% (DNP)
C19L: 0.1uF, 25V, X5R
D10N: SSB44-E3/52T
J10N: MOLEX 87703-0001 male
...

--------------------------------------------------

netlist> dbg
> /home/bunnie/work/netlist-checker/netlist-checker.py(429)<module>()
-> print "Netlist inspector v0.1"
(Pdb) cmd
'dbg'
(Pdb) pprint.pprint(pinCount[1])
['NET_ERROR']
(Pdb) 
