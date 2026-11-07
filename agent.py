import os
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from prompt import SYSTEM_PROMPT

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "_data-json_"


def load_json(file_name):
    file_path = DATA_DIR / file_name
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(text):
    text = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(
        character for character in text
        if not unicodedata.combining(character)
    )


def extract_max_price(question):
    normalized_question = normalize_text(question)
    match = re.search(
        r"\bate\s*(?:r\$\s*)?(\d[\d.]*(?:,\d{1,2})?)",
        normalized_question,
    )
    if not match:
        return None

    value = match.group(1).replace(".", "").replace(",", ".")
    return float(value)


def search_relevant_data(question, products, promotions, categories):
    ignored_terms = {
        "com", "como", "dos", "das", "uma", "uns", "para", "por",
        "que", "qual", "quais", "tem", "ter", "queria", "gostaria",
        "preco", "precos", "valor", "valores", "quanto", "mais",
        "menos", "barato", "barata", "caro", "cara", "me", "um",
        "de", "do", "da", "e", "em", "o", "a", "os", "as", "ate",
        "disponivel", "disponiveis", "custando", "custa",
    }
    terms = {
        term
        for term in re.findall(r"[a-z0-9]+", normalize_text(question))
        if len(term) > 2 and term not in ignored_terms
    }
    if not terms:
        return ""

    max_price = extract_max_price(question)
    category_map = {
        item["category_id"]: item["name"]
        for item in categories
    }
    results = []

    for product in products:
        if product.get("status") != "active" or product.get("stock_quantity", 0) <= 0:
            continue
        if max_price is not None and product.get("price_brl", float("inf")) > max_price:
            continue

        category = category_map.get(product.get("category_id"), "")
        product_text = normalize_text(" ".join([
            product.get("name", ""),
            product.get("description", ""),
            category,
            json.dumps(product.get("specs", {}), ensure_ascii=False),
        ]))
        score = sum(
            bool(re.search(rf"\b{re.escape(term)}\b", product_text))
            for term in terms
        )
        if score:
            results.append((score, product, category))

    results.sort(key=lambda item: (-item[0], item[1]["price_brl"]))
    selected_products = [product for _, product, _ in results[:10]]
    if not selected_products:
        return (
            "\n\nDADOS RELEVANTES DO CATÁLOGO: "
            "nenhum produto ativo e disponível corresponde à busca "
            "e ao limite de preço informado."
        )

    product_ids = {product["product_id"] for product in selected_products}
    active_promotions = [
        promotion for promotion in promotions
        if promotion.get("is_active") and promotion.get("product_id") in product_ids
    ]
    return (
        "\n\nDADOS RELEVANTES DO CATÁLOGO (use apenas se forem úteis):\n"
        + json.dumps(
            {
                "produtos": [
                    {
                        **product,
                        "categoria": category_map.get(
                            product.get("category_id"), ""
                        ),
                    }
                    for product in selected_products
                ],
                "promocoes_ativas": active_promotions,
            },
            ensure_ascii=False,
        )
    )


# Keep this validation local so order data is not sent to Gemini.
def get_order_status_response(question, orders, customers):
    normalized_question = normalize_text(question)
    status_keywords = {
        "status", "rastrear", "rastreamento", "chegou", "acompanhar",
        "localizar", "onde", "enviado", "andamento",
    }
    if "pedido" not in normalized_question or not any(
        keyword in normalized_question for keyword in status_keywords
    ):
        return None

    order_number = re.search(
        r"\bpedido(?:\s*(?:n(?:[ºo.]*)|#))?\s*(\d+)\b",
        normalized_question,
    )
    email = re.search(
        r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
        question,
        re.IGNORECASE,
    )
    if not order_number or not email:
        return (
            "Para consultar com segurança, envie o número do pedido e o "
            "e-mail cadastrado na compra. Não compartilhe sua senha ou dados "
            "de pagamento."
        )

    order = next(
        (
            item for item in orders
            if str(item.get("order_id")) == order_number.group(1)
        ),
        None,
    )
    if not order:
        return (
            "Não encontrei um pedido que corresponda a esses dados. "
            "Confira o número e o e-mail cadastrado ou fale com nossa equipe."
        )

    customer = next(
        (
            item for item in customers
            if item.get("customer_id") == order.get("customer_id")
        ),
        None,
    )
    if not customer or normalize_text(customer.get("email", "")) != normalize_text(email.group(0)):
        return (
            "Não encontrei um pedido que corresponda a esses dados. "
            "Confira o número e o e-mail cadastrado ou fale com nossa equipe."
        )

    readable_status = {
        "pending": "aguardando confirmação",
        "processing": "em preparação",
        "shipped": "enviado",
        "delivered": "entregue",
        "cancelled": "cancelado",
    }.get(order.get("status"), "em atualização")
    response = f"Encontrei seu pedido: ele está {readable_status}."

    estimated_delivery = order.get("estimated_delivery")
    if estimated_delivery:
        formatted_delivery = date.fromisoformat(estimated_delivery).strftime("%d/%m/%Y")
        response += f" A previsão de entrega registrada é {formatted_delivery}."

    tracking_code = order.get("tracking_code")
    if tracking_code:
        response += f" Código de rastreio: {tracking_code}."
    return response


# Create the Gemini connection only when the support session starts.
def create_chat():
    from dotenv import load_dotenv
    from google import genai

    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY não encontrada. Configure a variável no arquivo .env."
        )

    policy_text = (DATA_DIR / "politicas_da_loja.md").read_text(
        encoding="utf-8"
    )
    system_context = (
        f"{SYSTEM_PROMPT}\n\nMANUAL DE POLÍTICAS DA LOJA:\n{policy_text}"
    )
    client = genai.Client(api_key=api_key)
    return client.chats.create(
        model="gemini-3.8-flash",
        config={
            "system_instruction": system_context,
            "temperature": 0.3,
        },
    )


def start_chat():
    print("Carregando bases de dados da Empório da Música...")
    products = load_json("products.json")
    promotions = load_json("promotions.json")
    categories = load_json("categories.json")
    orders = load_json("orders.json")
    customers = load_json("customers.json")
    chat = create_chat()

    print("\n" + "=" * 60)
    print("🎸 Olá! O Buddy (Assistente da Empório da Música) está online.")
    print("Digite sua mensagem para conversar ou digite 'sair' para encerrar.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_message = input("Cliente: ")
            if user_message.strip().lower() in ["sair", "exit", "quit"]:
                print("\nBuddy: Foi um prazer ajudar! Volte sempre à Empório da Música. 🎶")
                break

            if not user_message.strip():
                continue

            order_response = get_order_status_response(
                user_message, orders, customers
            )
            if order_response is not None:
                print(f"\nBuddy: {order_response}\n" + "-" * 40)
                continue

            catalog_context = search_relevant_data(
                user_message, products, promotions, categories
            )
            response = chat.send_message(user_message + catalog_context)
            print(f"\nBuddy: {response.text}\n" + "-" * 40)

        except KeyboardInterrupt:
            print("\n\nEncerrando o atendimento do Buddy. Até mais!")
            break
        except Exception as error:
            print(f"\nOps! Ocorreu um erro ao processar sua mensagem: {error}\n")


if __name__ == "__main__":
    start_chat()
