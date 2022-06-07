import binascii
from tokenize import Hexnumber

from erdpy.accounts import Account
from erdpy.proxy import ElrondProxy
from erdpy.transactions import Transaction

import argparse

import pandas as pd

pd.options.mode.chained_assignment = None  # default='warn'

# ---------------------------------------------------------------- #
#                         INPUTS
# ---------------------------------------------------------------- #
parser = argparse.ArgumentParser()
parser.add_argument("--filename", help="CSV file with two cols : Address and Count", required=True)
parser.add_argument("--amount_airdrop", help="The total amount of ESDT to be airdropped", required=True)
parser.add_argument("--id", help="The collection id of the ESDT (The last 6 alphanumericals)", required=True)
parser.add_argument("--pem", help="The wallet that sends txs (needs to hold the ESDT)", required=True)

args = parser.parse_args()

# Read the input file
data_df = pd.read_csv(args.filename)

# If not done already, remove SC addresses
eligible_holders = data_df[data_df.Address.apply(lambda x: "qqqqqq" not in x)]

# Compute the total of ESDT per address (given the number of NFT hold)
# TMP FIX : Remove 0.1 ESDT per NFT to avoid "insufficient funds" (due to Python's loss of precision)
airdrop_per_NFT = float(args.amount_airdrop) / (eligible_holders.Count.sum())
eligible_holders["Airdrop"] = airdrop_per_NFT * data_df.Count

# ---------------------------------------------------------------- #
#                         CONSTANTS
# ---------------------------------------------------------------- #
TOKEN_DECIMALS = 1000000000000000000  # 10^18 (18 decimals)
TOKEN_COLLECTION = "AERO-458bbf"
TOKEN_ID = args.id
MESSAGE = "June 2022 Helios Mitya Distribution"


# ---------------------------------------------------------------- #
#                         HELPER FUNCTIONS
# ---------------------------------------------------------------- #
def text_to_hex(text):
    return binascii.hexlify(text.encode()).decode()


# Sometimes need to add a 0 (if it's even, to be sure that is grouped by bytes)
def num_to_hex(num):
    hexa = format(num, "x")
    if len(hexa) % 2 == 1:
        return "0" + hexa
    return hexa


def int_to_BigInt(num):
    return int(f"{num * TOKEN_DECIMALS:.1f}".split(".")[0])


# ---------------------------------------------------------------- #
#                   MAIN LKMEX FONCTION
# ---------------------------------------------------------------- #
def sendLKMEX(owner, receiver, amount):
    payload = "ESDTTransfer@" + "@".join([text_to_hex(TOKEN_COLLECTION),
                                          num_to_hex(int_to_BigInt(amount)),
                                          receiver.address.hex(),
                                          text_to_hex(MESSAGE)])

    tx = Transaction()
    tx.nonce = owner.nonce
    tx.value = "0"
    tx.sender = owner.address.bech32()
    tx.receiver = receiver.address.bech32()
    tx.gasPrice = gas_price
    tx.gasLimit = 600000
    tx.data = payload
    tx.chainID = chain
    tx.version = tx_version

    tx.sign(owner)
    tx_hash = tx.send(proxy)
    owner.nonce += 1
    return tx_hash


# ---------------------------------------------------------------- #
#                  SETTING MAINNET PARAMS
# ---------------------------------------------------------------- #
proxy_address = "https://gateway.elrond.com"
proxy = ElrondProxy(proxy_address)
network = proxy.get_network_config()
chain = network.chain_id
gas_price = network.min_gas_price
tx_version = network.min_tx_version

# The owner of the tokens, that will send them
owner = Account(pem_file=args.pem)
owner.sync_nonce(proxy)

# ---------------------------------------------------------------- #
#                     AIRDROP LOOP
# ---------------------------------------------------------------- #
for _, row in eligible_holders.iterrows():

    quantity = row["Airdrop"]
    address = row["Address"]

    try:
        sendLKMEX(owner, Account(address), quantity)
    except:
        # Keep those addresses aside for debugging, and re-sending after 
        print(address)
