# Capturas de tela

As imagens desta pasta são geradas pelo teste de navegador
(`apps/atendimento/tests/test_navegador.py`), não montadas à mão:

```bash
python -m playwright install chromium
RODAR_TESTES_DE_NAVEGADOR=1 python manage.py test apps.atendimento.tests.test_navegador
```

Cada captura é tirada depois que o teste verificou o estado daquela tela. Se a
tela quebrar, o teste falha antes de salvar a imagem.

| Arquivo | Momento do fluxo |
|---|---|
| `01-garcom-rascunho.png` | Garçom (390px) com dois itens no rascunho, ainda não enviados |
| `02-garcom-enviado.png` | Depois do envio: itens confirmados no servidor, rascunho vazio |
| `03-caixa-comanda.png` | Caixa (desktop) com a comanda da mesa 5 aberta |
| `04-caixa-pagamento.png` | Diálogo de pagamento em dinheiro, com troco calculado |
| `05-caixa-historico.png` | Histórico com a comanda encerrada |
