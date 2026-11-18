# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, users

from odoo.addons.base.tests.common import BaseCommon


class TestAccountLockDateUpdate(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.adviser_group = cls.env.ref("account.group_account_manager")
        new_test_user(
            cls.env, login="test_lock_date_user", groups="account.group_account_manager"
        )
        new_test_user(
            cls.env, login="test_billing_user", groups="account.group_account_user"
        )
        new_test_user(
            cls.env,
            login="test_auditor_user",
            groups="account.group_account_readonly",
        )

    @users("test_lock_date_user")
    def test_01_update_with_access(self):
        wizard = self.env["account.update.lock_date"].create(
            {"company_id": self.company.id}
        )
        wizard.write(
            {
                "sale_lock_date": "2000-05-01",
                "purchase_lock_date": "2000-04-01",
                "tax_lock_date": "2000-03-01",
                "fiscalyear_lock_date": "2000-02-01",
                "hard_lock_date": "2000-01-01",
            }
        )
        wizard.execute()
        self.assertEqual(
            fields.Date.to_string(self.company.sale_lock_date), "2000-05-01"
        )
        self.assertEqual(
            fields.Date.to_string(self.company.purchase_lock_date), "2000-04-01"
        )
        self.assertEqual(
            fields.Date.to_string(self.company.tax_lock_date), "2000-03-01"
        )
        self.assertEqual(
            fields.Date.to_string(self.company.fiscalyear_lock_date), "2000-02-01"
        )
        self.assertEqual(
            fields.Date.to_string(self.company.hard_lock_date), "2000-01-01"
        )

    @users("test_billing_user")
    def test_02_update_without_access(self):
        # A user who is not an adviser (manager) cannot even open the wizard to write.
        with self.assertRaises(AccessError):
            self.env["account.update.lock_date"].create(
                {"company_id": self.company.id, "sale_lock_date": "2000-05-01"}
            )

    @users("test_auditor_user")
    def test_03_auditor_cannot_write(self):
        # The auditor reads the wizard but cannot create it, so no date can be set.
        with self.assertRaises(AccessError):
            self.env["account.update.lock_date"].create(
                {"company_id": self.company.id, "sale_lock_date": "2000-05-01"}
            )

    @users("test_lock_date_user")
    def test_04_future_date_refused(self):
        future = fields.Date.add(fields.Date.context_today(self.env.user), days=10)
        wizard = self.env["account.update.lock_date"].create(
            {"company_id": self.company.id, "sale_lock_date": future}
        )
        with self.assertRaises(UserError):
            wizard.execute()
        self.assertNotEqual(self.company.sale_lock_date, future)

    @users("test_lock_date_user")
    def test_05_default_get_shows_current_dates(self):
        self.company.sudo().write({"sale_lock_date": "2000-05-01"})
        wizard = self.env["account.update.lock_date"].create(
            {"company_id": self.company.id}
        )
        self.assertEqual(fields.Date.to_string(wizard.sale_lock_date), "2000-05-01")

    def test_06_unreconciled_redirect_action_has_views(self):
        # The core action of Odoo 20 has no "views" key, which breaks the client
        # when it is shown from the lock date error; the override adds them.
        action = self.company._get_unreconciled_statement_lines_redirect_action(
            self.env["account.bank.statement.line"]
        )
        self.assertEqual(action["res_model"], "account.move")
        self.assertTrue(action["views"])
        self.assertEqual({view_type for _id, view_type in action["views"]}, {"list", "form"})

