# Arquitetura e decisões

O README descreve o que o sistema faz. Este arquivo explica por que ele é assim.

---

## 1. Organização em três apps

| App | Responsabilidade |
|---|---|
| `apps.cardapio` | Catálogo: `Categoria`, `Produto`, `Adicional` |
| `apps.atendimento` | Operação de salão: `Mesa`, `Comanda`, `Envio`, `ItemComanda`, `Pagamento` |
| `apps.clientes` | Site público |

A separação segue a fronteira do domínio, não a camada técnica. O catálogo é
cadastro: muda devagar, é editado pela administração, e sua regra principal é
"este produto pode ser vendido agora?". A operação é transacional: muda a cada
minuto, tem concorrência, dinheiro e histórico. Misturar os dois em um app só
significaria que qualquer mudança de preço mexe no mesmo módulo que fecha conta.

Dentro de `atendimento`, as responsabilidades também estão separadas:

```
models.py         persistência e restrições
formularios.py    validação do que chega do navegador
servicos.py       regras de negócio e transações
api.py            HTTP, permissão e tratamento de erro
views.py          telas
perfis.py         grupos e permissões
valores.py        aritmética de dinheiro
```

`servicos.py` é o **único** módulo que escreve comanda, item e pagamento. A
consequência prática: a mesma regra vale para a API, para o admin e para os
testes. Não existe caminho alternativo que grave um item pulando a validação.

---

## 2. Catálogo: um `Produto`, não uma classe por tipo

Um modelo por tipo de produto (`Pizza`, `Cerveja`, `Refrigerante`,
`Sobremesa`...) parece orientação a objetos, mas é **dado modelado como
classe**. Todos teriam os mesmos campos — nome, descrição, categoria, preço,
imagem — e cadastrar um tipo novo exigiria escrever uma classe, gerar migração e
alterar o endpoint que lista itens.

Pior: o endpoint precisaria descobrir, em tempo de execução, qual modelo atende
cada categoria. Isso significa uma consulta por modelo, resultado dependente da
ordem de registro dos apps, e comportamento indefinido quando uma categoria tem
mais de um modelo associado.

Com `Categoria` + `Produto`, a diferença entre uma pizza e um refrigerante é o
valor de um campo. Cadastrar um tipo novo é preencher um formulário no admin.

**Onde a herança continua fazendo sentido:** a classe abstrata `Registro`
(`criado_em`, `atualizado_em`, `ativo`), que injeta colunas de auditoria nas
filhas sem virar tabela. Herança para compartilhar comportamento comum: sim.
Herança para representar tipos que só diferem em dados: não.

**Regra de venda concentrada em um lugar:**

```python
class ProdutoQuerySet(models.QuerySet):
    def vendaveis(self):
        return self.filter(ativo=True, disponivel=True, categoria__ativo=True)
```

O mesmo `vendaveis()` alimenta o cardápio público, a tela do garçom e a
validação do envio. Três consumidores, uma definição.

**Dois campos de disponibilidade, de propósito:** `ativo` é cadastro (o produto
saiu do cardápio), `disponivel` é hoje (acabou). O primeiro é decisão de
gerência, o segundo é operação — e um produto inativado nunca é apagado, porque
vendas antigas apontam para ele.

---

## 3. Itens: entidade, não campo JSON

Guardar os itens de uma comanda em um `JSONField` funciona até a primeira
pergunta séria. Não dá para cancelar um item específico mantendo histórico, nem
saber quem lançou cada um, nem responder "quanto vendemos de X no mês" sem ler e
interpretar JSON, nem garantir no banco que a quantidade é um inteiro positivo.

`ItemComanda` é tabela, com chave estrangeira e restrições. Mas o JSON não
desapareceu: ele ficou em `ItemComanda.adicionais_detalhe`, e apenas ali — como
**retrato histórico** dos adicionais praticados na venda.

A distinção é o ponto: o que precisa ser validado, consultado e relacionado
virou coluna; o que precisa apenas ser preservado exatamente como estava no dia
da venda ficou em JSON.

---

## 4. Preço calculado no servidor

O navegador envia identificadores, quantidades e escolhas. Nunca preço, nunca
total.

```python
class ItemEnviadoForm(forms.Form):
    produto = forms.ModelChoiceField(queryset=Produto.objects.none())
    produto_secundario = forms.ModelChoiceField(queryset=Produto.objects.none(), required=False)
    quantidade = forms.IntegerField(min_value=1)
    observacao = forms.CharField(max_length=140, required=False)
    adicionais = forms.ModelMultipleChoiceField(queryset=Adicional.objects.none(), required=False)
```

Não existe campo de preço, então um `preco` no corpo da requisição não tem por
onde entrar — não é filtrado, é inexistente. Os querysets são montados no
`__init__` e não na definição da classe, para refletirem a disponibilidade no
momento do envio.

O servidor então busca o produto, confirma que está ativo e disponível, confirma
que cada adicional é permitido naquela categoria, e calcula.

A tela do garçom mostra um subtotal previsto enquanto o item é montado. Ele
espelha a regra do servidor, mas é conforto visual: o valor que vale é o que
volta na resposta do envio.

### Meia a meia

```python
def preco_do_item(produto, produto_secundario):
    if produto_secundario is None:
        return dinheiro(produto.preco)

    a, b = dinheiro(produto.preco), dinheiro(produto_secundario.preco)
    if settings.ATENDIMENTO_REGRA_MEIO_A_MEIO == 'media':
        return dinheiro((a + b) / 2)
    return max(a, b)
```

Cobra o sabor mais caro. É a regra mais comum no mercado brasileiro — impede que
um sabor caro seja diluído metade a metade com um barato. Fica configurável
porque é decisão comercial, não técnica: trocar entre "maior" e "média" não
deveria exigir deploy de código novo. Há teste para as duas opções.

---

## 5. Dinheiro em `Decimal`

`float` é binário: `0.1 + 0.2` vale `0.30000000000000004`. Em uma conta de
restaurante isso vira diferença de centavo no fechamento do caixa.

`valores.py` concentra três funções — `dinheiro`, `somar`, `formatar_brl` — e a
regra: **duas casas decimais, ROUND_HALF_UP**, o arredondamento comercial.

O arredondamento acontece **uma vez por linha**, no subtotal do item, e os
subtotais já arredondados são somados. Assim o total não depende da ordem em que
os itens foram lançados — há teste que monta a mesma comanda em duas ordens
diferentes e compara.

---

## 6. Uma comanda aberta por mesa

```python
models.UniqueConstraint(
    fields=['mesa'],
    condition=models.Q(status='aberta'),
    name='unica_comanda_aberta_por_mesa',
)
```

`get_or_create` faz um SELECT e, se não achar, um INSERT. Entre os dois existe
uma janela em que duas requisições simultâneas passam pelos dois SELECTs antes
de qualquer INSERT — e ambas criam. Uma verificação no código não fecha essa
janela; uma restrição no banco fecha.

A condição é o que torna a restrição utilizável: vale só para comandas abertas,
então a mesma mesa acumula dezenas de comandas pagas no histórico e no máximo
uma aberta. Quem perde a corrida recebe `IntegrityError` e
`abrir_ou_recuperar_comanda` relê a comanda que o outro criou.

O teste correspondente não chama o serviço: vai direto ao modelo e espera o
`IntegrityError`. Ele testa a garantia, não a implementação.

---

## 7. Estado da mesa é derivado

`Mesa` não tem campo de status. `Mesa.ocupada` é uma consulta: existe comanda
aberta?

Guardar `Mesa.status` em paralelo ao status da comanda cria duas fontes de
verdade atualizadas por códigos diferentes, e nada impede uma mesa "livre" com
comanda aberta. Estado duplicado é estado que diverge.

---

## 8. Idempotência do envio

O problema real: o garçom aperta "Enviar", o celular perde o sinal no meio, e
ele não sabe se gravou. Apertar de novo pode duplicar a rodada; não apertar pode
perder o pedido.

O navegador gera um UUID quando o rascunho recebe o primeiro item e só o
descarta quando o servidor confirma. A tabela `Envio` tem esse UUID com
restrição única. O serviço:

1. procura o `Envio` com essa referência;
2. se já existe, devolve o resultado daquele envio e **não grava nada**;
3. se não existe, valida tudo, cria o `Envio` e grava os itens — em uma
   transação.

Duas requisições idênticas em paralelo: a segunda leva `IntegrityError` na
criação do `Envio` e cai no mesmo caminho de "já processado".

Na interface, falha de rede não limpa o rascunho. Aparece um aviso dizendo que
**não é possível saber** se gravou, com dois botões: "Consultar comanda no
servidor" e "Tentar enviar novamente" — que reenvia a mesma referência. O
usuário precisa enxergar a diferença entre "deu erro" e "não sei se deu certo".

---

## 9. Preço histórico

`ItemComanda` guarda `descricao`, `preco_unitario`, `preco_adicionais` e
`adicionais_detalhe` no momento da venda, **além** da chave estrangeira para
`Produto`.

A chave serve para relatório ("quanto vendemos de X"); o retrato serve para a
conta. Mudar o preço do catálogo amanhã não altera uma conta fechada hoje.

É desnormalização deliberada: preço histórico é o caso clássico em que a
duplicação é o requisito, não um descuido.

`on_delete=PROTECT` completa: um produto já vendido não pode ser apagado, só
inativado. Histórico não perde linha porque alguém limpou o cadastro.

---

## 10. Pagamento e encerramento

- `Pagamento` é `OneToOne` com `Comanda`. Pagamento duplicado é impedido pelo
  banco. O serviço verifica antes para dar mensagem legível, mas a garantia
  final é a restrição.
- O valor cobrado é **recalculado** dentro da transação, a partir dos itens
  gravados. O que o navegador mandar como total é ignorado.
- Em dinheiro, `valor`, `valor_recebido` e `troco` são três campos distintos, e
  o servidor recusa valor recebido menor que a conta.
- Pix e cartão são registros manuais, rotulados como tal no modelo, na tela e
  aqui. Nenhum número de cartão, código de segurança ou credencial é gravado.
- Pagamento e encerramento acontecem na **mesma transação**: não existe estado
  em que a comanda foi encerrada sem pagamento gravado, ou o contrário.
- Comanda sem consumo não pode ser paga; ela é cancelada, com motivo, e não
  conta como venda.
- No admin, `Pagamento` é somente leitura — não dá para adicionar, editar nem
  apagar. Histórico financeiro editável não é histórico.

---

## 11. Perfis e autorização

Quem autentica é `django.contrib.auth.User`; perfil é grupo do Django; senha é
sempre hash (PBKDF2). Não existe modelo de usuário paralelo — duas fontes de
verdade para autenticação é um problema de segurança esperando acontecer.

Permissões customizadas ficam em `Comanda.Meta.permissions`:

```python
permissions = [
    ('lancar_itens', 'Pode abrir comanda e lançar itens'),
    ('cancelar_item', 'Pode cancelar item já enviado'),
    ('registrar_pagamento', 'Pode registrar pagamento e encerrar comanda'),
    ('ver_historico_financeiro', 'Pode consultar o histórico financeiro'),
]
```

`perfis.sincronizar_grupos()` cria os três grupos com suas permissões e pode
rodar quantas vezes for preciso.

A interface esconde botões que o perfil não pode usar — conforto, não proteção.
A autorização real está em cada endpoint, e há testes que chamam a URL com
sessão de garçom e verificam 403 mais a ausência do registro no banco.

Outro garçom pode continuar o atendimento de qualquer mesa: quem lançou fica
registrado por item (`ItemComanda.criado_por`), sem travar a mesa no primeiro.

---

## 12. Interface

- CSS próprio, uma folha só, servida pelo próprio servidor. A tela do garçom não
  pode depender de um CDN estar acessível no celular, dentro do salão.
- Botões com no mínimo 44px de altura na tela do garçom.
- Itens **já enviados** e itens **em rascunho** em blocos visualmente distintos.
  O garçom remove livremente o que é rascunho; o que foi enviado só o caixa
  cancela, com motivo.
- O caixa abre os detalhes com **um clique** — duplo clique em tela sensível ao
  toque é quase inacessível.
- Polling de 10 segundos, **suspenso enquanto um diálogo está aberto**: nada
  apaga o que o operador está digitando.
- Falha de atualização aparece no indicador com botão de tentar de novo, em vez
  de a tela congelar mostrando dado velho.
- Estado nunca depende só de cor: cada etiqueta traz símbolo e texto
  ("● Livre", "● Ocupada", "✓ Paga", "✕ Cancelada").
- Todo campo tem `label`, o foco é visível, e há link "pular para o conteúdo".
- Nada é montado com `innerHTML` a partir de dado do servidor. Todo texto entra
  por `textContent`, então uma observação como `sem cebola <script>` aparece
  como texto.

---

## 13. Testes

`manage.py test` com `django.test.TestCase`: nenhuma dependência extra, banco de
teste criado e destruído automaticamente, cada teste dentro de uma transação
desfeita ao final, e o mesmo comando local e no CI. `pytest-django` traria
fixtures mais expressivas, mas não resolve nenhum problema que exista aqui.

Os testes miram **garantias**, não implementação. O de atomicidade, por exemplo,
simula uma falha no meio da gravação e verifica que nem o envio nem os itens
sobreviveram:

```python
with mock.patch.object(ItemComanda.objects, 'bulk_create', side_effect=RuntimeError):
    with self.assertRaises(RuntimeError):
        servicos.enviar_itens(comanda.pk, REF, [...], usuario)

self.assertEqual(Envio.objects.filter(comanda=comanda).count(), 0)
self.assertEqual(ItemComanda.objects.filter(comanda=comanda).count(), 0)
```

Sem transação, esse teste falharia deixando o registro de envio órfão.

### Uma armadilha que vale conhecer

Uma suíte que descobre **zero** testes termina com código de saída 0 e imprime
`OK`. Verde, sem ter executado nada.

Acontece quando um diretório do projeto não tem `__init__.py`: para importar,
o Python trata a pasta como *namespace package* e funciona; para a descoberta de
testes, não — o suporte a namespace packages foi removido do `unittest` no
Python 3.11.

Por isso `apps/__init__.py` existe, e por isso o CI falha se a saída contiver
`Ran 0 tests` ou não contiver `Ran N tests`. Uma suíte vazia que passa é pior do
que suíte nenhuma: dá confiança sem dar evidência.

### Verificação em navegador

Separada da suíte do dia a dia porque exige o Chromium do Playwright. Percorre a
jornada com duas sessões independentes — garçom em 390px e caixa em desktop,
cookies separados — e falha se o console registrar qualquer erro. As capturas do
README saem dessa execução.

---

## 14. Banco de dados

O projeto declara **um** banco: SQLite. A decisão é consciente e tem limite
claro.

SQLite serializa escritas: enquanto uma transação de escrita está aberta, as
outras esperam (aqui, até 15 segundos, via `timeout`). Para um restaurante com
poucos terminais, onde a escrita é curta e esporádica, isso basta — e as
restrições que garantem a consistência (comanda aberta única, envio único,
pagamento único) são aplicadas pelo banco em qualquer um dos dois.

O que SQLite **não** oferece é a concorrência de escrita do PostgreSQL nem
`SELECT ... FOR UPDATE` real: ali, `select_for_update()` é aceito pelo Django
mas não trava linha individual. É exatamente por isso que a garantia de "uma
comanda aberta por mesa" está em uma `UniqueConstraint` condicional, e não em
uma leitura seguida de gravação — a constraint funciona nos dois bancos.

Migrar para PostgreSQL exige trocar `DATABASES`, instalar o driver e **rodar os
testes lá**. Compatibilidade que não foi medida não é afirmada.
