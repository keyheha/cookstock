import pandas as pd
from enum import Enum
import io
import requests

_EXCHANGE_LIST = ['nyse', 'nasdaq', 'amex']

_SECTORS_LIST = {'Consumer Non-Durables', 'Capital Goods', 'Health Care', 'Energy', 'Technology', 'Basic Industries',
                 'Finance', 'Consumer Services', 'Public Utilities', 'Miscellaneous', 'Consumer Durables',
                 'Transportation'}

# Custom ticker lists
CUSTOM_TICKERS_US = [
    # === US SECTOR ETFs ===
    # SPDR Select Sector ETFs (11 sectors)
    'XLB',    # Materials
    'XLC',    # Communication Services
    'XLE',    # Energy
    'XLF',    # Financials
    'XLI',    # Industrials
    'XLK',    # Technology
    'XLP',    # Consumer Staples
    'XLRE',   # Real Estate
    'XLU',    # Utilities
    'XLV',    # Health Care
    'XLY',    # Consumer Discretionary
    
    # Vanguard Sector ETFs
    'VCR',    # Consumer Discretionary
    'VDC',    # Consumer Staples
    'VDE',    # Energy
    'VFH',    # Financials
    'VGT',    # Information Technology
    'VHT',    # Health Care
    'VIS',    # Industrials
    'VOX',    # Communication Services
    'VAW',    # Materials
    'VNQ',    # Real Estate
    'VPU',    # Utilities
    
    # === US INDUSTRY ETFs ===
    # Technology Sub-Sectors
    'SOXX',   # Semiconductors
    'SMH',    # Semiconductors
    'SOXQ',   # Semiconductors (NASDAQ-100)
    'IGV',    # Software
    'WCLD',   # Cloud Computing
    'SKYY',   # Cloud Computing
    'HACK',   # Cybersecurity
    'CIBR',   # Cybersecurity
    'BUG',    # Cybersecurity
    'AIQ',    # AI & Big Data
    'BOTZ',   # Robotics & AI
    'ROBT',   # Robotics & Automation
    'FINX',   # Fintech
    'ARKF',   # Fintech Innovation
    'CLOU',   # Cloud Computing
    'AWAY',   # Travel Technology
    
    # Financial Sub-Sectors
    'KRE',    # Regional Banks
    'KBE',    # Banks
    'IAT',    # Regional Banks
    'KBWB',   # Banks
    'KIE',    # Insurance
    'IAK',    # Insurance
    'FNCL',   # Financials
    'IYF',    # Financials
    'VFH',    # Financials
    'IYG',    # Financial Services
    'SPYV',   # S&P 500 Value
    
    # Healthcare Sub-Sectors
    'IBB',    # Biotech
    'XBI',    # Biotech
    'BBH',    # Biotech
    'IHI',    # Medical Devices
    'IHE',    # Pharma
    'XPH',    # Pharma
    'GNOM',   # Genomics
    'ARKG',   # Genomic Revolution
    
    # Energy Sub-Sectors
    'XOP',    # Oil & Gas Exploration
    'IEO',    # Oil & Gas Exploration
    'OIH',    # Oil Services
    'IEZ',    # Oil Equipment & Services
    'ICLN',   # Clean Energy
    'TAN',    # Solar Energy
    'FAN',    # Wind Energy
    'PBW',    # Clean Energy
    'QCLN',   # Clean Energy
    'ACES',   # Clean Energy
    'LIT',    # Lithium & Battery Tech
    'BATT',   # Battery Tech & Materials
    
    # Industrial Sub-Sectors
    'ITB',    # Homebuilders
    'XHB',    # Homebuilders
    'IYT',    # Transportation
    'XTN',    # Transportation
    'JETS',   # Airlines
    'ITA',    # Aerospace & Defense
    'PPA',    # Aerospace & Defense
    'ARKX',   # Space Exploration
    'UFO',    # Space & Defense
    
    # Consumer Sub-Sectors
    'XRT',    # Retail
    'RTH',    # Retail
    'XLY',    # Consumer Discretionary
    'FXD',    # Consumer Discretionary
    'ONLN',   # Online Retail
    'IBUY',   # Online Retail
    'AWAY',   # Travel & Leisure
    'PEJ',    # Leisure & Entertainment
    'GAMR',   # Video Games & Esports
    'ESPO',   # Video Gaming & Esports
    'BJK',    # Gaming
    
    # Materials & Commodities
    'GDX',    # Gold Miners
    'GDXJ',   # Junior Gold Miners
    'SLV',    # Silver
    'GLD',    # Gold
    'SIL',    # Silver Miners
    'COPX',   # Copper Miners
    'PICK',   # Metals & Mining
    'XME',    # Metals & Mining
    'REMX',   # Rare Earth/Strategic Metals
    
    # Real Estate Sub-Sectors
    'IYR',    # Real Estate
    'XLRE',   # Real Estate
    'VNQ',    # Real Estate
    'MORT',   # Mortgage REITs
    'REZ',    # Residential REITs
    'INDS',   # Industrial REITs
    'HOMZ',   # Residential Construction
    
    # Communication Services
    'SOCL',   # Social Media
    'FIVG',   # 5G Networks
    'NXTG',   # 5G
    
    # === S&P 500 STOCKS ===
    # Mega Cap Tech (Top 10)
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'V', 'UNH',
    
    # Technology
    'AVGO', 'ORCL', 'ADBE', 'CRM', 'ACN', 'CSCO', 'AMD', 'INTC', 'IBM', 'NOW',
    'INTU', 'QCOM', 'AMAT', 'TXN', 'MU', 'ADI', 'LRCX', 'KLAC', 'SNPS', 'CDNS',
    'PANW', 'NXPI', 'MCHP', 'FTNT', 'ADSK', 'ANSS', 'ROP', 'KEYS', 'APH', 'TEL',
    'ANET', 'MPWR', 'TYL', 'ZBRA', 'AKAM', 'CTSH', 'DELL', 'HPQ', 'NTAP', 'STX',
    'WDC', 'FFIV', 'JNPR', 'ENPH', 'SEDG', 'ON', 'SWKS', 'QRVO', 
    
    # Communication Services
    'META', 'GOOGL', 'GOOG', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR',
    'EA', 'TTWO', 'WBD', 'NWSA', 'NWS', 'FOXA', 'FOX', 'OMC', 'IPG', 'PARA',
    'MTCH', 'LYV',
    
    # Consumer Discretionary
    'AMZN', 'TSLA', 'HD', 'NKE', 'MCD', 'SBUX', 'LOW', 'TJX', 'BKNG', 'AZO',
    'CMG', 'ORLY', 'MAR', 'GM', 'F', 'ABNB', 'YUM', 'DHI', 'LEN', 'HLT',
    'ROST', 'DG', 'DLTR', 'EBAY', 'ETSY', 'BBY', 'ULTA', 'DPZ', 'GPC', 'POOL',
    'KMX', 'CZR', 'LVS', 'WYNN', 'MGM', 'TSCO', 'PHM', 'TPR', 'RL', 'HAS',
    'GRMN', 'WHR', 'NVR', 'EXPE', 'NCLH', 'RCL', 'CCL', 'AAL', 'DAL', 'UAL',
    'LUV', 'ALK',
    
    # Consumer Staples
    'PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'MDLZ', 'CL', 'GIS',
    'KMB', 'MNST', 'SYY', 'KHC', 'HSY', 'K', 'CAG', 'TSN', 'CHD', 'CLX',
    'CPB', 'HRL', 'MKC', 'SJM', 'LW', 'TAP', 'EL', 'KDP', 'BG', 'ADM',
    
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'PXD', 'VLO', 'WMB',
    'OKE', 'KMI', 'HAL', 'BKR', 'FANG', 'HES', 'DVN', 'MRO', 'OXY', 'APA',
    
    # Financials
    'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'C', 'SPGI',
    'AXP', 'BLK', 'SCHW', 'CB', 'MMC', 'PGR', 'AON', 'ICE', 'CME', 'USB',
    'PNC', 'TFC', 'COF', 'AIG', 'MET', 'PRU', 'AFL', 'ALL', 'TRV', 'AMP',
    'FIS', 'BK', 'STT', 'TROW', 'BEN', 'IVZ', 'NTRS', 'KEY', 'RF', 'CFG',
    'FITB', 'HBAN', 'MTB', 'SIVB', 'ZION', 'WBS', 'CMA', 'PBCT', 'DFS', 'SYF',
    'ALLY', 'JKHY', 'AJG', 'BRO', 'WRB', 'RJF', 'CINF', 'L', 'GL', 'AIZ',
    
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'ABBV', 'PFE', 'TMO', 'MRK', 'ABT', 'DHR', 'AMGN',
    'BMY', 'GILD', 'CVS', 'CI', 'ELV', 'ISRG', 'VRTX', 'ZTS', 'REGN', 'MDT',
    'SYK', 'BSX', 'HUM', 'MRNA', 'EW', 'BDX', 'IDXX', 'ALGN', 'HCA', 'CNC',
    'A', 'DXCM', 'IQV', 'RMD', 'ILMN', 'BIIB', 'STE', 'MTD', 'ZBH', 'BAX',
    'HOLX', 'PODD', 'TECH', 'COO', 'INCY', 'WAT', 'VTRS', 'CRL', 'PKI', 'DGX',
    'LH', 'MOH', 'TFX', 'WST', 'HSIC', 'RVTY', 'CAH', 'MCK', 'COR', 'UHS',
    
    # Industrials
    'UNP', 'RTX', 'HON', 'UPS', 'BA', 'LMT', 'DE', 'CAT', 'GE', 'MMM',
    'GD', 'NOC', 'ETN', 'ITW', 'EMR', 'CSX', 'NSC', 'FDX', 'CARR', 'PCAR',
    'WM', 'TDG', 'RSG', 'URI', 'ODFL', 'JCI', 'CMI', 'PWR', 'FAST', 'PAYX',
    'VRSK', 'ROK', 'OTIS', 'AME', 'DOV', 'FTV', 'IR', 'XYL', 'LDOS', 'SWK',
    'CHRW', 'EXPD', 'JBHT', 'DAL', 'UAL', 'AAL', 'LUV', 'ALK', 'NLSN', 'IEX',
    'PNR', 'TXT', 'ROL', 'ALLE', 'MAS', 'AOS', 'GNRC', 'WAB', 'NDSN', 'J',
    
    # Materials
    'LIN', 'APD', 'SHW', 'ECL', 'DD', 'FCX', 'NEM', 'DOW', 'NUE', 'VMC',
    'MLM', 'CTVA', 'PPG', 'IFF', 'ALB', 'BALL', 'AVY', 'EMN', 'CF', 'MOS',
    'FMC', 'CE', 'IP', 'WRK', 'PKG', 'SEE', 'AMCR',
    
    # Real Estate
    'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'WELL', 'SBAC', 'DLR', 'O', 'SPG',
    'VICI', 'EQR', 'AVB', 'WY', 'INVH', 'ARE', 'VTR', 'EXR', 'MAA', 'ESS',
    'KIM', 'UDR', 'HST', 'REG', 'FRT', 'BXP', 'CPT', 'PEAK',
    
    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'EXC', 'XEL', 'ED', 'PEG',
    'ES', 'WEC', 'DTE', 'PPL', 'AWK', 'AEE', 'FE', 'EIX', 'ETR', 'CMS',
    'CNP', 'NI', 'LNT', 'EVRG', 'ATO', 'AES', 'PNW', 'NRG', 'CEG',
]

CUSTOM_TICKERS_UK = [
    # --- FTSE 100 ---
    'III.L', 'ADM.L', 'AAF.L', 'ALW.L', 'AAL.L', 'ANTO.L', 'AHT.L', 'ABF.L', 'AZN.L', 'AUTO.L',
    'AV.L', 'BAB.L', 'BA.L', 'BARC.L', 'BTRW.L', 'BEZ.L', 'BKG.L', 'BP.L', 'BATS.L', 'BLND.L',
    'BT-A.L', 'BNZL.L', 'BRBY.L', 'CNA.L', 'CCEP.L', 'CCH.L', 'CPG.L', 'CTEC.L', 'CRDA.L', 'DCC.L',
    'DGE.L', 'DPLM.L', 'EZJ.L', 'EDV.L', 'ENT.L', 'EXPN.L', 'FCIT.L', 'FRES.L', 'GAW.L', 'GLEN.L',
    'GSK.L', 'HLN.L', 'HLMA.L', 'HIK.L', 'HSX.L', 'HWDN.L', 'HSBA.L', 'ICG.L', 'IHG.L', 'IMB.L',
    'IMI.L', 'INF.L', 'IAG.L', 'ITRK.L', 'JD.L', 'KGF.L', 'LAND.L', 'LGEN.L', 'LLOY.L', 'LSEG.L',
    'MKS.L', 'MRO.L', 'MNDI.L', 'NG.L', 'NWG.L', 'NXT.L', 'OCDO.L', 'PSON.L', 'PSH.L', 'PHNX.L',
    'PRU.L', 'RKT.L', 'REL.L', 'REN.L', 'RIO.L', 'RR.L', 'RS1.L', 'SBRY.L', 'SGE.L', 'SRE.L',
    'SGRO.L', 'SHEL.L', 'SMDS.L', 'SMIN.L', 'SN.L', 'SPX.L', 'SSE.L', 'STAN.L', 'STJ.L', 'SVT.L',
    'TSCO.L', 'ULVR.L', 'UU.L', 'VTYV.L', 'VOD.L', 'WEIR.L', 'WTB.L', 'WPP.L',

    # --- FTSE 250 (Full List Selection) ---
    '3IN.L', 'FOUR.L', 'ABDN.L', 'ASL.L', 'AAS.L', 'ALFA.L', 'ATT.L', 'AEP.L', 'AO.L', 'APN.L',
    'ASHM.L', 'AIE.L', 'AML.L', 'ATYM.L', 'AGT.L', 'AVON.L', 'BME.L', 'BGF.L', 'BBY.L', 'BCG.L',
    'BNKR.L', 'BAG.L', 'AJB.L', 'BWY.L', 'BHMG.L', 'BYG.L', 'BPCR.L', 'BRGE.L', 'BRSC.L', 'THRG.L',
    'BRWM.L', 'BSIF.L', 'BOY.L', 'BREE.L', 'BPT.L', 'BUT.L', 'BYIT.L', 'CCR.L', 'CLDN.L', 'CGT.L',
    'CCL.L', 'CWR.L', 'CHG.L', 'CSN.L', 'CHRY.L', 'CTY.L', 'CKN.L', 'CLIG.L', 'CLI.L', 'COA.L',
    'CCC.L', 'CURY.L', 'DARK.L', 'DNL.L', 'DPH.L', 'DLN.L', 'DIG9.L', 'DOM.L', 'DRX.L', 'DOW.L',
    'DWW.L', 'ECM.L', 'EDIN.L', 'EMG.L', 'ENOG.L', 'EPIC.L', 'ESNT.L', 'EUO.L', 'EWI.L', 'FGP.L',
    'FDM.L', 'FSG.L', 'FGT.L', 'FRCL.L', 'GCP.L', 'GFT.L', 'GNS.L', 'GPEG.L', 'GRG.L', 'HBR.L',
    'HAYS.L', 'HICL.L', 'HOCM.L', 'HRI.L', 'IBST.L', 'IGG.L', 'IEM.L', 'IMCP.L', 'INCH.L', 'INVP.L',
    'IP.L', 'IWG.L', 'ITV.L', 'JDW.L', 'JMAT.L', 'JLEN.L', 'JGGI.L', 'JGI.L', 'JMG.L', 'JUP.L',
    'KIE.L', 'LRE.L', 'LTI.L', 'MCG.L', 'MAB.L', 'MTO.L', 'MGNS.L', 'NESV.L', 'N91.L', 'OSB.L',
    'OXIG.L', 'PAGE.L', 'PNN.L', 'PFD.L', 'PHP.L', 'PNL.L', 'QLT.L', 'QQ.L', 'RAT.L', 'RCP.L',
    'RDW.L', 'RRE.L', 'RCH.L', 'RNK.L', 'RWI.L', 'SAFE.L', 'SVS.L', 'SDRL.L', 'SRP.L', 'SHB.L',
    'SHI.L', 'SMWH.L', 'SOFT.L', 'SONC.L', 'SREI.L', 'SSP.L', 'STCK.L', 'SXS.L', 'TATE.L',
    'TBCG.L', 'TPK.L', 'TIG.L', 'TRY.L', 'UKW.L', 'VCTX.L', 'VSVS.L', 'VNET.L', 'WIZZ.L', 'WOSG.L',

    # --- UK AI & DIGITAL INFRASTRUCTURE (Specialized) ---
    # 'BYIT.L',  # Bytes Technology - Cloud & AI licensing infrastructure
    # 'CCC.L',  # Computacenter - Enterprise IT & AI hardware rollout
    # 'SGRO.L', # Segro - Leading Data Center REIT (Physical sites)
    # 'AHT.L',  # Ashtead - Power & cooling for data center builds
    # 'RR.L',  # Rolls-Royce - SMR (Small Modular Reactors) for AI energy needs
    'KAI.L',  # Kainos - Leading AI implementation services
    # 'OXIG.L',  # Oxford Instruments - Semiconductors/Nanotech research tools
    'RSW.L',  # Renishaw - High-precision engineering for AI hardware/robotics
    # 'CWR.L',  # Ceres Power - Fuel cell tech for off-grid data center power
    # 'SGE.L',  # Sage Group - Enterprise AI workflow infrastructure
    'FTC.L'  # Filtronic - High-frequency comms infrastructure for AI clusters

    # RIO.L, GLEN.L, AAL.L, ANTO.L, SHEL.L, BP.L,
    # EDV.L, KLR.L, FXPO.L,
    # CNA.L, HBR.L, WG.L, ITH.L
]

CUSTOM_TICKERS_HK = [
    '0001.HK',  # 長江和記
    '0002.HK',  # 中電控股
    '0003.HK',  # 香港中華煤氣
    '0005.HK',  # 匯豐控股
    '0006.HK',  # 電能實業
    '0011.HK',  # 恆生銀行
    '0012.HK',  # 恆基地產
    '0016.HK',  # 新鴻基地產
    '0017.HK',  # 新世界發展
    '0027.HK',  # 銀河娛樂
    '0066.HK',  # 港鐵公司
    '0101.HK',  # 恆隆地產
    '0175.HK',  # 吉利汽車
    '0241.HK',  # 阿里健康
    '0267.HK',  # 中信股份
    '0285.HK',  # 比亞迪電子
    '0288.HK',  # 萬洲國際
    '0291.HK',  # 華潤啤酒
    '0316.HK',  # 東方海外國際
    '0322.HK',  # 康師傅控股
    '0386.HK',  # 中國石油化工
    '0388.HK',  # 香港交易所
    '0669.HK',  # 創科實業
    '0688.HK',  # 中國海外發展
    '0700.HK',  # 騰訊控股
    '0762.HK',  # 中國聯通
    '0823.HK',  # 領展房產基金
    '0857.HK',  # 中國石油股份
    '0868.HK',  # 信義玻璃
    '0883.HK',  # 中國海洋石油
    '0939.HK',  # 建設銀行
    '0941.HK',  # 中國移動
    '0960.HK',  # 龍湖集團
    '0968.HK',  # 信義光能
    '0981.HK',  # 中芯國際
    '0992.HK',  # 聯想集團
    '1024.HK',  # 快手-W
    '1038.HK',  # 長江基建集團
    '1044.HK',  # 恆安國際
    '1088.HK',  # 中國神華
    '1093.HK',  # 石藥集團
    '1109.HK',  # 華潤置地
    '1113.HK',  # 長江實業集團
    '1177.HK',  # 中國生物製藥
    '1209.HK',  # 華潤萬象生活
    '1211.HK',  # 比亞迪股份
    '1299.HK',  # 友邦保險
    '1347.HK',  # 華虹半導體
    '1378.HK',  # 中國宏橋
    '1398.HK',  # 工商銀行
    '1797.HK',  # 東方甄選
    '1810.HK',  # 小米集團
    '1876.HK',  # 百威亞太
    '1928.HK',  # 金沙中國有限公司
    '1929.HK',  # 周大福
    '2013.HK',  # 微盟集團
    '2015.HK',  # 理想汽車-W
    '2020.HK',  # 安踏體育
    '2269.HK',  # 藥明生物
    '2313.HK',  # 申洲國際
    '2318.HK',  # 中國平安
    '2319.HK',  # 蒙牛乳業
    '2331.HK',  # 李寧
    '2382.HK',  # 舜宇光學科技
    '2388.HK',  # 中銀香港
    '2628.HK',  # 中國人壽
    '2688.HK',  # 新奧能源
    '3690.HK',  # 美團-W
    '3968.HK',  # 招商銀行
    '3988.HK',  # 中國銀行
    '6060.HK',  # 眾安在線
    '6098.HK',  # 碧桂園服務
    '6618.HK',  # 京東健康
    '6690.HK',  # 海爾智家
    '6862.HK',  # 海底撈
    '9618.HK',  # 京東集團-SW
    '9626.HK',  # 嗶哩嗶哩-W
    '9633.HK',  # 農夫山泉
    '9866.HK',  # 蔚來-SW
    '9868.HK',  # 小鵬汽車-W
    '9888.HK',  # 百度集團-SW
    '9922.HK',  # 九毛九
    '9961.HK',  # 攜程集團-S
    '9988.HK',  # 阿里巴巴-SW
    '9999.HK'  # 網易-S
]

CUSTOM_TICKERS_HK_OTHERS = [
    '0008.HK',  # 電訊盈科
    '2018.HK',  # 瑞聲科技
    '2400.HK',  # 心動公司
    '2638.HK',  # 港燈電力投資
    '3306.HK',  # 江南布衣
    '3328.HK',  # 交通銀行
    '6823.HK',  # 香港電訊
    '9660.HK'  # 地平線
]

# headers and params used to bypass NASDAQ's anti-scraping mechanism in function __exchange2df
# headers = {
#     'authority': 'old.nasdaq.com',
#     'upgrade-insecure-requests': '1',
#     'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
#     'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
#     'sec-fetch-site': 'cross-site',
#     'sec-fetch-mode': 'navigate',
#     'sec-fetch-user': '?1',
#     'sec-fetch-dest': 'document',
#     'referer': 'https://github.com/shilewenuw/get_all_tickers/issues/2',
#     'accept-language': 'en-US,en;q=0.9',
#     'cookie': 'AKA_A2=A; NSC_W.TJUFEFGFOEFS.OBTEBR.443=ffffffffc3a0f70e45525d5f4f58455e445a4a42378b',
# }

headers = {
    'authority': 'api.nasdaq.com',
    'accept': 'application/json, text/plain, */*',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
    'origin': 'https://www.nasdaq.com',
    'sec-fetch-site': 'same-site',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://www.nasdaq.com/',
    'accept-language': 'en-US,en;q=0.9',
}


def params(exchange):
    return (
        ('letter', '0'),
        ('exchange', exchange),
        ('render', 'download'),
    )


params = (
    ('tableonly', 'true'),
    ('limit', '25'),
    ('offset', '0'),
    ('download', 'true'),
)


def params_region(region):
    return (
        ('letter', '0'),
        ('region', region),
        ('render', 'download'),
    )


# I know it's weird to have Sectors as constants, yet the Regions as enums, but
# it makes the most sense to me
class Region(Enum):
    AFRICA = 'AFRICA'
    EUROPE = 'EUROPE'
    ASIA = 'ASIA'
    AUSTRALIA_SOUTH_PACIFIC = 'AUSTRALIA+AND+SOUTH+PACIFIC'
    CARIBBEAN = 'CARIBBEAN'
    SOUTH_AMERICA = 'SOUTH+AMERICA'
    MIDDLE_EAST = 'MIDDLE+EAST'
    NORTH_AMERICA = 'NORTH+AMERICA'


class SectorConstants:
    NON_DURABLE_GOODS = 'Consumer Non-Durables'
    CAPITAL_GOODS = 'Capital Goods'
    HEALTH_CARE = 'Health Care'
    ENERGY = 'Energy'
    TECH = 'Technology'
    BASICS = 'Basic Industries'
    FINANCE = 'Finance'
    SERVICES = 'Consumer Services'
    UTILITIES = 'Public Utilities'
    DURABLE_GOODS = 'Consumer Durables'
    TRANSPORT = 'Transportation'


# get tickers from chosen exchanges (default all) as a list
def get_custom_tickers(market='US'):
    """
    Get custom ticker list by market.
    
    Args:
        market (str): Market to get tickers for. Options: 'US', 'UK', 'HK', 'BOTH' (US+UK), 'ALL' (US+UK+HK)
    
    Returns:
        list: List of ticker symbols
    """
    market = market.upper()
    if market == 'US':
        return CUSTOM_TICKERS_US.copy()
    elif market == 'UK':
        return CUSTOM_TICKERS_UK.copy()
    elif market == 'HK':
        return CUSTOM_TICKERS_HK.copy() + CUSTOM_TICKERS_HK_OTHERS.copy()
    elif market == 'BOTH':
        return CUSTOM_TICKERS_US.copy() + CUSTOM_TICKERS_UK.copy()
    elif market == 'ALL':
        return CUSTOM_TICKERS_US.copy() + CUSTOM_TICKERS_UK.copy() + CUSTOM_TICKERS_HK.copy() + CUSTOM_TICKERS_HK_OTHERS.copy()
    else:
        raise ValueError(f"Invalid market '{market}'. Options: 'US', 'UK', 'HK', 'BOTH', 'ALL'")


def get_tickers(NYSE=True, NASDAQ=True, AMEX=True):
    tickers_list = []
    if NYSE:
        tickers_list.extend(__exchange2list('nyse'))
    if NASDAQ:
        tickers_list.extend(__exchange2list('nasdaq'))
    if AMEX:
        tickers_list.extend(__exchange2list('amex'))
    return tickers_list


def get_tickers_filtered(mktcap_min=None, mktcap_max=None, sectors=None):
    tickers_list = []
    for exchange in _EXCHANGE_LIST:
        tickers_list.extend(
            __exchange2list_filtered(exchange, mktcap_min=mktcap_min, mktcap_max=mktcap_max, sectors=sectors))
    return tickers_list


def get_biggest_n_tickers(top_n, sectors=None):
    df = pd.DataFrame()
    for exchange in _EXCHANGE_LIST:
        temp = __exchange2df(exchange)
        df = pd.concat([df, temp])

    df = df.dropna(subset={'marketCap'})
    df = df[~df['Symbol'].str.contains("\.|\^")]

    if sectors is not None:
        if isinstance(sectors, str):
            sectors = [sectors]
        if not _SECTORS_LIST.issuperset(set(sectors)):
            raise ValueError('Some sectors included are invalid')
        sector_filter = df['Sector'].apply(lambda x: x in sectors)
        df = df[sector_filter]

    def cust_filter(mkt_cap):
        if 'M' in mkt_cap:
            return float(mkt_cap[1:-1])
        elif 'B' in mkt_cap:
            return float(mkt_cap[1:-1]) * 1000
        else:
            return float(mkt_cap[1:]) / 1e6

    df['marketCap'] = df['marketCap'].apply(cust_filter)

    df = df.sort_values('marketCap', ascending=False)
    if top_n > len(df):
        raise ValueError('Not enough companies, please specify a smaller top_n')

    return df.iloc[:top_n]['Symbol'].tolist()


def get_tickers_by_region(region):
    if region in Region:
        response = requests.get('https://old.nasdaq.com/screening/companies-by-name.aspx', headers=headers,
                                params=params_region(region))
        data = io.StringIO(response.text)
        df = pd.read_csv(data, sep=",")
        return __exchange2list(df)
    else:
        raise ValueError('Please enter a valid region (use a Region.REGION as the argument, e.g. Region.AFRICA)')


def __exchange2df(exchange):
    # response = requests.get('https://old.nasdaq.com/screening/companies-by-name.aspx', headers=headers, params=params(exchange))
    # data = io.StringIO(response.text)
    # df = pd.read_csv(data, sep=",")
    r = requests.get('https://api.nasdaq.com/api/screener/stocks', headers=headers, params=params)
    data = r.json()['data']
    df = pd.DataFrame(data['rows'], columns=data['headers'])
    return df


def __exchange2list(exchange):
    df = __exchange2df(exchange)
    # removes weird tickers
    df_filtered = df[~df['symbol'].str.contains("\.|\^")]
    return df_filtered['symbol'].tolist()


# market caps are in millions
def __exchange2list_filtered(exchange, mktcap_min=None, mktcap_max=None, sectors=None):
    df = __exchange2df(exchange)
    # df = df.dropna(subset={'MarketCap'})
    df = df.dropna(subset={'marketCap'})
    df = df[~df['symbol'].str.contains("\.|\^")]

    if sectors is not None:
        if isinstance(sectors, str):
            sectors = [sectors]
        if not _SECTORS_LIST.issuperset(set(sectors)):
            raise ValueError('Some sectors included are invalid')
        sector_filter = df['sector'].apply(lambda x: x in sectors)
        df = df[sector_filter]

    def cust_filter(mkt_cap):
        if 'M' in mkt_cap:
            return float(mkt_cap[1:-1])
        elif 'B' in mkt_cap:
            return float(mkt_cap[1:-1]) * 1000
        elif mkt_cap == '':
            return 0.0
        else:
            return float(mkt_cap[1:]) / 1e6

    df['marketCap'] = df['marketCap'].apply(cust_filter)
    if mktcap_min is not None:
        df = df[df['marketCap'] > mktcap_min]
    if mktcap_max is not None:
        df = df[df['marketCap'] < mktcap_max]
    return df['symbol'].tolist()


# save the tickers to a CSV
def save_tickers(NYSE=True, NASDAQ=True, AMEX=True, filename='tickers.csv'):
    tickers2save = get_tickers(NYSE, NASDAQ, AMEX)
    df = pd.DataFrame(tickers2save)
    df.to_csv(filename, header=False, index=False)


def save_tickers_by_region(region, filename='tickers_by_region.csv'):
    tickers2save = get_tickers_by_region(region)
    df = pd.DataFrame(tickers2save)
    df.to_csv(filename, header=False, index=False)


if __name__ == '__main__':
    # tickers of all exchanges
    tickers = get_tickers()
    print(tickers[:5])

    # tickers from NYSE and NASDAQ only
    tickers = get_tickers(AMEX=False)

    # default filename is tickers.csv, to specify, add argument filename='yourfilename.csv'
    save_tickers()

    # save tickers from NYSE and AMEX only
    save_tickers(NASDAQ=False)

    # get tickers from Asia
    tickers_asia = get_tickers_by_region(Region.ASIA)
    print(tickers_asia[:5])

    # save tickers from Europe
    save_tickers_by_region(Region.EUROPE, filename='EU_tickers.csv')

    # get tickers filtered by market cap (in millions)
    filtered_tickers = get_tickers_filtered(mktcap_min=500, mktcap_max=2000)
    print(filtered_tickers[:5])

    # not setting max will get stocks with $2000 million market cap and up.
    filtered_tickers = get_tickers_filtered(mktcap_min=2000)
    print(filtered_tickers[:5])

    # get tickers filtered by sector
    filtered_by_sector = get_tickers_filtered(mktcap_min=200e3, sectors=SectorConstants.FINANCE)
    print(filtered_by_sector[:5])

    # get tickers of 5 largest companies by market cap (specify sectors=SECTOR)
    top_5 = get_biggest_n_tickers(5)
    print(top_5)
