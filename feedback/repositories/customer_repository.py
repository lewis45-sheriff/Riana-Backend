"""Data access for Customer entities (Model layer)."""

from __future__ import annotations

from feedback.models import Customer


class CustomerRepository:
    def by_phone(self, phone: str) -> Customer | None:
        return Customer.objects.filter(phone=phone).first()

    def by_email(self, email: str) -> Customer | None:
        return Customer.objects.filter(email=email).first()

    def find_or_create(
        self, name: str, email: str | None, phone: str | None
    ) -> Customer:
        """Match by phone first, then email; otherwise create. Refresh contact."""
        customer: Customer | None = None
        if phone:
            customer = self.by_phone(phone)
        if customer is None and email:
            customer = self.by_email(email)
        if customer is None:
            return Customer.objects.create(name=name, email=email, phone=phone)
        customer.name = name or customer.name
        customer.email = email or customer.email
        customer.phone = phone or customer.phone
        customer.save()
        return customer
