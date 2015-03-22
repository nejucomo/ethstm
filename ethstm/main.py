#! /usr/bin/env python

import sys
import argparse
import logging
import json
import re


DESCRIPTION = """
ethstm, the ETHereum State Test Maker, generates state test specifications
from JSON templates which can automate the deterministic build and test
of multiple interacting smart contracts.
"""


def main(args = sys.argv[1:]):
    parse_args(args)

    trans = StateTestTranslator()
    jsonin = json.load(sys.stdin)
    jsonout = trans(jsonin)
    json.dump(jsonout, sys.stdout, sort_keys=True, indent=2)


def parse_args(args):
    p = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('--log-level',
                   dest='loglevel',
                   default='INFO',
                   choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
                   help='Set logging level.')

    opts = p.parse_args(args)

    logging.basicConfig(
        stream=sys.stdout,
        format='%(asctime)s %(levelname) 5s %(name)s | %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        level=getattr(logging, opts.loglevel))

    return opts


class SchemaError (Exception): pass

class StateTestTranslator (object):
    def __init__(self):
        self._log = logging.getLogger('trans')

        # Some Field parsers:
        Any = lambda x: x

        def Data(src):
            if len(src) == 0:
                return ''

            fields = src.split(':', 1)
            if len(fields) == 2:
                prefix, body = fields
                if prefix == 'hex':
                    return '0x' + body
                else:
                    raise SchemaError('Unknown data field prefix: {!r}'.format(prefix))
            else:
                raise SchemaError("Expected a single ':' in Data field: {!r}".format(src))


        # Regex fields:
        def rgx_field(name, pat):
            rgx = re.compile(pat)
            def parser(src):
                if rgx.match(src):
                    return src
                else:
                    raise SchemaError(
                        'Invalid {} field: {!r} does not match {}'.format(
                            name, src, pat))
            return parser

        Address   = rgx_field('Address',   r'[0-9a-f]{40}')
        SecretKey = rgx_field('SecretKey', r'[0-9a-f]{64}')
        UInt      = rgx_field('UInt',      r'\d+')

        Transaction = JSchema(
            data      = Data,
            gasLimit  = UInt,
            gasPrice  = UInt,
            nonce     = UInt,
            secretKey = SecretKey,
            to        = Address,
            value     = UInt,
            )

        TestCase = JSchema(
            env = Any,
            logs = Any,
            out = Any,
            post = Any,
            postStateRoot = Any,
            pre = Any,
            transaction = Transaction,
            )

        self._TestCases = JSchemaDict(str, TestCase)

    def __call__(self, jsonin):
        return self._TestCases(jsonin)


class JSchema (object):
    def __init__(self, **fieldspecs):
        self._fieldspecs = fieldspecs
        self._expectedkeys = set(self._fieldspecs.keys())

    def __call__(self, indoc):
        inkeys = set(indoc.keys())

        missingkeys = self._expectedkeys - inkeys
        unexpectedkeys = inkeys - self._expectedkeys
        if missingkeys or unexpectedkeys:
            raise SchemaError(
                'Missing keys: {!r}; unexpected keys: {!r}'.format(
                    missingkeys, unexpectedkeys))

        result = {}
        for (key, spec) in self._fieldspecs.iteritems():
            result[key] = spec(indoc[key])

        return result


class JSchemaDict (object):
    def __init__(self, keyspec, valspec):
        self._keyspec = keyspec
        self._valspec = valspec

    def __call__(self, indoc):
        result = {}
        for (kin, vin) in indoc.iteritems():
            kout = self._keyspec(kin)
            vout = self._valspec(vin)
            result[kout] = vout
        return result



if __name__ == '__main__':
    main()
