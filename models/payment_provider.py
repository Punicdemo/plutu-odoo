# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests
from werkzeug.urls import url_join
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.payment_plutu import const
_logger = logging.getLogger(__name__)



class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    name = fields.Char(string="Name", required=True, translate=True, readonly=True)
    state = fields.Selection(
        string="Status",
        help="In test mode, a fake payment is processed through a test payment interface.\n"
             "This mode is advised when setting up the provider.",
        selection=[('test', "Test Environment"), ('enabled', "Production Environment"), ('disabled', "Disabled")],
        default='disabled', required=True, copy=False)

    code = fields.Selection(
        selection_add=[('plutu', "Plutu")], ondelete={'plutu': 'set default'}
    )
    minimum_amount = fields.Monetary(
        string="Minimum Amount",
        help="The minimum payment amount that this payment provider is available. ",
        currency_field='main_currency_id', default=5, readonly=True)
    website_id = fields.Many2one(
        "website",
        check_company=True,
        ondelete="restrict",
        required_if_provider='plutu'
    )
    plutu_api_key = fields.Char(string="Plutu API Key", required_if_provider='plutu', groups='base.group_system')
    plutu_secret_key = fields.Char(string="Plutu Secret Key", required_if_provider='plutu', groups='base.group_system')
    plutu_access_token = fields.Char(string="Plutu Access Token", required_if_provider='plutu', groups='base.group_system')


    # === COMPUTE METHODS ===#


    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'plutu').update({
            'support_tokenization': True,
        })

    # === BUSINESS METHODS ===#

    @api.model
    def _find_available_providers(self, *args, is_validation=False, **kwargs):
        """ Override of `payment` to filter out paylink providers for validation operations. """
        providers = super()._find_available_providers(*args, is_validation=is_validation, **kwargs)

        if is_validation:
            providers = providers.filtered(lambda p: p.code != 'plutu')

        return providers
    
    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'plutu':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in
