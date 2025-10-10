def gerar_link_whatsapp(numero, mensagem):
    """
    Gera o link direto para enviar o pedido via WhatsApp.
    """
    mensagem_formatada = mensagem.replace(" ", "%20").replace("\n", "%0A")
    return f"https://wa.me/{numero}?text={mensagem_formatada}"
