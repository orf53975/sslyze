#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         PluginFallbackScsv.py
# Purpose:      Tests the server for supported SSL / TLS versions.
#
# Author:       bcyrill, alban
#
# Copyright:    2014 SSLyze developers
#
#   SSLyze is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   SSLyze is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with SSLyze.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from xml.etree.ElementTree import Element

from nassl import SSLV3, SSL_MODE_SEND_FALLBACK_SCSV, _nassl

from sslyze.plugins import PluginBase
from sslyze.plugins.PluginBase import PluginResult


class PluginFallbackScsv(PluginBase.PluginBase):

    interface = PluginBase.PluginInterface(title="PluginFallbackScsv", description="")
    interface.add_command(
        command="fallback",
        help="Checks support for the TLS_FALLBACK_SCSV cipher suite to prevent downgrade attacks."
    )


    def process_task(self, server_info, plugin_command, plugin_options=None):
        if server_info.ssl_version_supported <= SSLV3:
            raise ValueError('Server only supports SSLv3; no downgrade attacks are possible')

        # Try to connect using a lower TLS version with the fallback cipher suite enabled
        ssl_version_downgrade = server_info.ssl_version_supported - 1
        ssl_connection = server_info.get_preconfigured_ssl_connection(override_ssl_version=ssl_version_downgrade)
        ssl_connection.set_mode(SSL_MODE_SEND_FALLBACK_SCSV)

        supports_fallback_scsv = False
        try:
            # Perform the SSL handshake
            ssl_connection.connect()

        except _nassl.OpenSSLError as e:
            if 'tlsv1 alert inappropriate fallback' in str(e.args):
                supports_fallback_scsv = True
            else:
                raise

        finally:
            ssl_connection.close()

        return FallbackScsvResult(server_info, plugin_command, plugin_options, supports_fallback_scsv)


class FallbackScsvResult(PluginResult):

    COMMAND_TITLE = 'Downgrade Attacks'

    def __init__(self, server_info, plugin_command, plugin_options, supports_fallback_scsv):
        super(FallbackScsvResult, self).__init__(server_info, plugin_command, plugin_options)
        self.supports_fallback_scsv = supports_fallback_scsv

    def as_text(self):
        result_txt = [self.PLUGIN_TITLE_FORMAT(self.COMMAND_TITLE)]
        downgrade_txt = 'OK - Supported' \
            if self.supports_fallback_scsv \
            else 'VULNERABLE - Signaling cipher suite not supported'
        result_txt.append(self.FIELD_FORMAT('TLS_FALLBACK_SCSV:', downgrade_txt))
        return result_txt

    def as_xml(self):
        result_xml = Element(self.plugin_command, title=self.COMMAND_TITLE)
        result_xml.append(Element('tlsFallbackScsv', attrib={'isSupported': str(self.supports_fallback_scsv)}))
        return result_xml