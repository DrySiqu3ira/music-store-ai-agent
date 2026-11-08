import json
import unittest
from unittest.mock import Mock, patch

from agent import (
    create_chat,
    extract_max_price,
    get_order_status_response,
    load_json,
    search_relevant_data,
    start_chat,
)

class TestStoreAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = load_json("products.json")
        cls.promotions = load_json("promotions.json")
        cls.categories = load_json("categories.json")
        cls.orders = load_json("orders.json")
        cls.customers = load_json("customers.json")

    def test_extracts_max_price_in_brazilian_format(self):
        self.assertEqual(extract_max_price("violões até R$ 1.000,00"), 1000)

    def test_catalog_search_respects_price_and_availability(self):
        result = search_relevant_data(
            "Quais violões disponíveis até R$ 1.000,00?",
            self.products,
            self.promotions,
            self.categories,
        )
        data = json.loads(result.split(":\n", maxsplit=1)[1])

        self.assertTrue(data["produtos"])
        self.assertTrue(
            all(product["price_brl"] <= 1000 for product in data["produtos"])
        )
        self.assertTrue(
            all(
                product["status"] == "active" and product["stock_quantity"] > 0
                for product in data["produtos"]
            )
        )

    def test_order_lookup_without_email_requests_verification(self):
        response = get_order_status_response(
            "Qual o status do pedido 1?",
            self.orders,
            self.customers,
        )

        self.assertIn("e-mail cadastrado", response)
        self.assertNotIn("BRAB1234567BR", response)

    def test_order_lookup_with_matching_email_returns_status(self):
        order = next(item for item in self.orders if item["order_id"] == 1)
        customer = next(
            item for item in self.customers
            if item["customer_id"] == order["customer_id"]
        )
        response = get_order_status_response(
            f"Qual o status do pedido 1? Meu e-mail é {customer['email']}",
            self.orders,
            self.customers,
        )

        self.assertIn("entregue", response)
        self.assertIn(order["tracking_code"], response)
        self.assertNotIn(customer["email"], response)

    def test_order_lookup_with_wrong_email_does_not_reveal_data(self):
        response = get_order_status_response(
            "Qual o status do pedido 1? Meu e-mail é pessoa@exemplo.com",
            self.orders,
            self.customers,
        )

        self.assertIn("Não encontrei um pedido", response)
        self.assertNotIn("BRAB1234567BR", response)

    def test_non_status_question_is_not_intercepted(self):
        response = get_order_status_response(
            "Quero saber como funciona a devolução do pedido",
            self.orders,
            self.customers,
        )

        self.assertIsNone(response)

    # Confirm that order lookups stay local and do not call Gemini.
    def test_order_lookup_does_not_call_gemini(self):
        order = next(item for item in self.orders if item["order_id"] == 1)
        customer = next(
            item for item in self.customers
            if item["customer_id"] == order["customer_id"]
        )
        message = (
            f"Qual o status do pedido 1? Meu e-mail é {customer['email']}"
        )
        with (
            patch("agent.create_chat") as create_chat,
            patch("builtins.input", side_effect=[message, "sair"]),
            patch("builtins.print"),
        ):
            create_chat.return_value = (Mock(), Mock())
            start_chat()

        client, chat = create_chat.return_value
        chat.send_message.assert_not_called()
        client.close.assert_called_once()

    def test_chat_keeps_client_open_until_session_ends(self):
        order = next(item for item in self.orders if item["order_id"] == 1)
        customer = next(
            item for item in self.customers
            if item["customer_id"] == order["customer_id"]
        )
        inputs = [
            "Quais violões vocês têm?",
            f"Qual o status do pedido 1? Meu e-mail é {customer['email']}",
            "sair",
        ]
        client = Mock()
        chat = Mock()

        with (
            patch("agent.create_chat", return_value=(client, chat)),
            patch("builtins.input", side_effect=inputs),
            patch("builtins.print"),
        ):
            start_chat()

        chat.send_message.assert_called_once()
        client.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
