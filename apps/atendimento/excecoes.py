"""Erros de negócio previstos, com código estável para o front-end."""


class ErroDeNegocio(Exception):
    """Situação que o usuário pode entender e corrigir.

    Nunca carrega detalhe interno (SQL, caminho de arquivo, stack trace):
    a mensagem é escrita para aparecer em tela.
    """

    status_http = 400
    codigo = 'erro_de_negocio'

    def __init__(self, mensagem, codigo=None, status_http=None, detalhes=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        if codigo:
            self.codigo = codigo
        if status_http:
            self.status_http = status_http
        self.detalhes = detalhes or {}

    def como_dicionario(self):
        return {
            'ok': False,
            'codigo': self.codigo,
            'erro': self.mensagem,
            'detalhes': self.detalhes,
        }


class DadosInvalidos(ErroDeNegocio):
    status_http = 400
    codigo = 'dados_invalidos'


class NaoEncontrado(ErroDeNegocio):
    status_http = 404
    codigo = 'nao_encontrado'


class OperacaoNaoPermitida(ErroDeNegocio):
    status_http = 403
    codigo = 'operacao_nao_permitida'


class ConflitoDeEstado(ErroDeNegocio):
    """A operação é válida, mas não neste estado (comanda encerrada, já paga...)."""

    status_http = 409
    codigo = 'conflito_de_estado'
