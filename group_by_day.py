# -*- coding: utf-8 -*-
"""

This script groups trades that occur on the same day. To allow grouping, ecords must have:

 - the same currency pair
 - the same exchange
 - the same date

The script does NOT work on the API but processes a csv file. This is useful for
reporting margin trades as described here: https://cointracking.freshdesk.com/en/support/solutions/articles/29000018275-margin-trades-profit-determination

Expected csv input format (set this up by selecting the right columns in the "Trade List"):

     Buy amount, Buy currency, Buy in EUR, Sell amount, Sell currency, Sell in EUR, Exchange, Date

For example:

    1.95852928, BTC, 114.87092795, 1312.95150627, XMR, 116.15735953, Poloniex, 30.08.2016 13:31

Output format is the same.
"""
import csv
import sys

from decimal import Decimal


class Record(object):
    exchange_exceptions = ["Wallet", "Transaction"]  # E.g. don't process autoimported blockchain transactions

    def __init__(self, record_type, buyamt, buycur, sellamt, sellcur, fee, fee_cur, exchange, group, comment, date, tx_id):
        self.record_type = record_type
        self.buyamt = Decimal(buyamt) if buyamt else None
        self.buycur = buycur
        self.sellamt = Decimal(sellamt) if sellamt else None
        self.sellcur = sellcur
        self.fee = Decimal(fee) if fee else None
        self.fee_cur = fee_cur
        self.exchange = exchange
        self.group = group
        self.comment = comment
        self.date = date.strip()  # Store full date and time
        self.tx_id = tx_id

    def __str__(self):
        """
        Exports as csv row.
        """
        buyamt_str = str(self.buyamt) if self.buyamt is not None else ''
        sellamt_str = str(self.sellamt) if self.sellamt is not None else ''
        fee_str = str(self.fee) if self.fee is not None else ''
        
        return "{},{},{},{},{},{},{},{},{},{},{},{}".format(self.record_type, buyamt_str, self.buycur,
                                                sellamt_str, self.sellcur, fee_str, self.fee_cur,
                                                self.exchange, self.group, self.comment, self.date, self.tx_id)

    def __eq__(self, other):
        """
        Returns True if two records can be combined (same currencies, same venue, same date)
        """
        # Check if the exchange contains any of the exception strings (case insensitive)
        if any(exc.lower() in self.exchange.lower() for exc in self.exchange_exceptions):
            return False  # They are not equal if the self exchange contains any exception string

        res = (self.record_type == other.record_type and
               self.buycur == other.buycur and
               self.sellcur == other.sellcur and
               self.exchange == other.exchange and
               self.fee_cur == other.fee_cur and
               self.date.split(' ')[0] == other.date.split(' ')[0])  # Compare only the date part
        return res

    def __add__(self, other):
        """
        Adds two records by adding amounts only.
        Populates group and comment if one has a value and the other doesn't.
        """
        group = self.group if self.group else other.group
        comment = self.comment if self.comment else other.comment
        
        # Debugging: Print self and other if any of the amounts are None
        # if self.buyamt is None or other.buyamt is None:
        #     print("Debug: self =", self, "other =", other, "buyamt is None")
        # if self.sellamt is None or other.sellamt is None:
        #     print("Debug: self =", self, "other =", other, "sellamt is None")
        # if self.fee is None or other.fee is None:
        #     print("Debug: self =", self, "other =", other, "fee is None")
        
        # Set to None if either is None
        buyamt_sum = None if self.buyamt is None or other.buyamt is None else (self.buyamt + other.buyamt)
        sellamt_sum = None if self.sellamt is None or other.sellamt is None else (self.sellamt + other.sellamt)
        fee_sum = None if self.fee is None or other.fee is None else (self.fee + other.fee)
        
        return Record(self.record_type, buyamt_sum, self.buycur,
                      sellamt_sum, self.sellcur, fee_sum,
                      self.fee_cur, self.exchange, group, comment, self.date, self.tx_id)


def process_csv(input_file, output_file):
    output = []
    previous = None
    header = None

    with open(input_file) as csvfile:
        csvdata = csv.reader(csvfile, delimiter=',')

        for row in csvdata:
            if header is None:
                header = row
                continue

            record = Record(*row)
            if previous is None:
                previous = record
                continue

            if record.record_type == "Lost" and record.exchange == "Binance" and "_fee" in record.tx_id:
                continue # ignore redundant binance "lost" type fee
            elif record == previous:
                previous += record
                continue
            else:
                output.append(previous)
                previous = record

        output.append(previous)

    with open(output_file, 'w') as csvfile:
        if header is not None:  # Ensure header is not None
            csvfile.writelines(','.join(header) + '\n')
        else:
            raise ValueError("Header is not initialized properly.")
        for record in output:
            csvfile.write(str(record) + '\n')

    print("Exported {} records.".format(len(output)))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: {} <csv_in> <csv_out>".format(sys.argv[0]))
        exit(1)

    process_csv(sys.argv[1], sys.argv[2])