def main():
    import os

    from dotenv import load_dotenv
    from google import genai

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "Erro: A variável GEMINI_API_KEY não foi encontrada. "
            "Verifique o arquivo .env."
        )
        return

    print("Chave encontrada com sucesso! Testando conexão com o Gemini...")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents="Diga 'Conexão bem-sucedida com o Gemini!' em uma frase curta.",
        )
        print("Resposta do Gemini:", response.text)
    except Exception as error:
        print(f"Ocorreu um erro ao conectar com a API: {error}")


# Keep the external API call out of automatic test discovery.
if __name__ == "__main__":
    main()