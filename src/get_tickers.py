import pandas as pd
from enum import Enum
import io
import requests

_EXCHANGE_LIST = ['nyse', 'nasdaq', 'amex']

_SECTORS_LIST = set(['Consumer Non-Durables', 'Capital Goods', 'Health Care',
                     'Energy', 'Technology', 'Basic Industries', 'Finance',
                     'Consumer Services', 'Public Utilities', 'Miscellaneous',
                     'Consumer Durables', 'Transportation'])

# Custom ticker lists
CUSTOM_TICKERS_US = [
    # Combined from personal watchlist, AI infrastructure, and major US companies
    'AAOI', 'AAPL', 'ABT', 'ABBV', 'ABNB', 'ACN', 'ADBE', 'ADSK', 'AI', 'ALAB',
    'AMAT', 'AMD', 'AMT', 'AMZN', 'ANET', 'APH', 'APLD', 'ARM', 'ASML', 'AVGO',
    'BA', 'BAC', 'BASE', 'BE',
    'C', 'CEG', 'CIEN', 'CIFR', 'CLS', 'CMCSA', 'COHR', 'COIN', 'COST', 'CRDO',
    'CRM', 'CRWD', 'CRWV', 'CSCO', 'CVX',
    'DDOG', 'DELL', 'DIS', 'DOCN', 'DOCU', 'DUOL', 'DUK',
    'EA', 'EBAY', 'EOSE', 'EQR', 'ETSY', 'EXPE',
    'FDX', 'FLEX', 'FLNC', 'FN', 'FRSH',
    'GEV', 'GILD', 'GLXY', 'GOOG', 'GOOGL', 'GTLB',
    'HD', 'HON', 'HOOD', 'HUT',
    'IBM', 'INTC', 'INTU', 'IREN',
    'JNJ', 'JPM',
    'KEY', 'KO',
    'LEU', 'LITE', 'LLY',
    'MA', 'MCD', 'MDB', 'META', 'MNDY', 'MRK', 'MRNA', 'MS', 'MSFT', 'MU', 'MMM',
    'NBIS', 'NEE', 'NET', 'NFLX', 'NKE', 'NOW', 'NTAP', 'NUAI', 'NVDA',
    'O', 'OKLO', 'OKTA', 'ORCL',
    'PEP', 'PG', 'PHM', 'PINS', 'PLTR', 'PM', 'PSTG', 'PSX', 'PYPL',
    'QCOM',
    'RBLX', 'RKLB', 'ROKU', 'RTX',
    'SANM', 'SBUX', 'SHOP', 'SMTC', 'SNAP', 'SNDK', 'SNOW', 'SPG', 'SPGI', 'SPOT',
    'SQ', 'STX',
    'TEAM', 'TEM', 'TGT', 'TLN', 'TMO', 'TSLA', 'TSM', 'TTD', 'TWLO', 'TXN',
    'UBER', 'UDMY', 'UNH', 'UNP', 'UPS', 'UPWK',
    'V', 'VEEV', 'VMEO', 'VRT', 'VST', 'VZ',
    'WDC', 'WIX', 'WMT', 'WULF',
    'XOM'
]

CUSTOM_TICKERS_UK = [
    # Combined from AI Infrastructure, FTSE 100, and custom UK tickers
    'AAF.L', 'AAL.L', 'ABF.L', 'ADM.L', 'AHT.L', 'ANTO.L', 'AUTO.L', 'AV.L', 'AZN.L',
    'BA.L', 'BAB.L', 'BAKK.L', 'BARC.L', 'BATS.L', 'BBOX.L', 'BDEV.L', 'BEZ.L', 'BHP.L',
    'BLND.L', 'BNZL.L', 'BP.L', 'BRBY.L', 'BT.A.L', 'BWY.L', 'BYIT.L',
    'CCH.L', 'CKN.L', 'CNA.L', 'CORD.L', 'CPG.L', 'CRDA.L', 'CRH.L',
    'DCC.L', 'DGE.L', 'DIG9.L', 'DPLM.L', 'DRX.L',
    'EXPN.L',
    'FERG.L', 'FLTR.L', 'FRES.L',
    'GAW.L', 'GLEN.L', 'GSK.L',
    'HIK.L', 'HL.L', 'HLMA.L', 'HSBA.L', 'HWDN.L',
    'IAG.L', 'ICG.L', 'IHG.L', 'IMB.L', 'IMI.L', 'INF.L', 'III.L', 'ITRK.L',
    'JD.L', 'JET.L', 'JMAT.L',
    'KGF.L',
    'LAND.L', 'LGEN.L', 'LLOY.L', 'LSEG.L',
    'MKS.L', 'MNG.L', 'MNDI.L', 'MRO.L', 'MTC.L',
    'NG.L', 'NWG.L', 'NXT.L',
    'OCDO.L', 'OXIG.L',
    'PHNX.L', 'PNN.L', 'POLY.L', 'PRU.L', 'PSH.L', 'PSN.L', 'PSON.L',
    'REL.L', 'REN.L', 'RIO.L', 'RKT.L', 'RMV.L', 'RR.L', 'RSA.L', 'RTO.L',
    'SBRY.L', 'SDR.L', 'SGE.L', 'SGRO.L', 'SHEL.L', 'SLA.L', 'SMDS.L', 'SMIN.L',
    'SMT.L', 'SN.L', 'SPX.L', 'SSE.L', 'STAN.L', 'STJ.L', 'SVT.L', 'SXS.L',
    'TSCO.L', 'TW.L',
    'UKW.L', 'ULVR.L', 'UU.L',
    'VOD.L',
    'WEIR.L', 'WPP.L', 'WTB.L'
]

CUSTOM_TICKERS_HK = [
    '0005.HK',  # HSBC Holdings
    '0008.HK',  # PCCW
    '0285.HK',  # BYD Electronics
    '0388.HK',  # Hong Kong Exchanges and Clearing (HKEX)
    '0700.HK',  # Tencent Holdings
    '0981.HK',  # SMIC (Semiconductor Manufacturing International)
    '0992.HK',  # Lenovo Group
    '1024.HK',  # Kuaishou Technology
    '1398.HK',  # Industrial and Commercial Bank of China (ICBC)
    '1810.HK',  # Xiaomi Corporation
    '2018.HK',  # AAC Technologies
    '2638.HK',  # HK Electric Investments
    '3328.HK',  # Bank of Communications
    '3690.HK',  # Meituan
    '6823.HK',  # HKT (Hong Kong Telecommunications)
    '9626.HK',  # Bilibili
    '9660.HK',  # Horizon Robotics
    '9888.HK',  # Baidu
    '9988.HK',  # Alibaba Group
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
        return CUSTOM_TICKERS_HK.copy()
    elif market == 'BOTH':
        return CUSTOM_TICKERS_US.copy() + CUSTOM_TICKERS_UK.copy()
    elif market == 'ALL':
        return CUSTOM_TICKERS_US.copy() + CUSTOM_TICKERS_UK.copy() + CUSTOM_TICKERS_HK.copy()
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