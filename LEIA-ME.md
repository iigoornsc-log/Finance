# CFO Pessoal — atualizações

## 1) Por que os dados sumiam no Render

O Render usa disco **efêmero** nos planos padrão: toda vez que o serviço reinicia
(deploy novo, sleep por inatividade, restart automático), o sistema de arquivos
volta ao estado da imagem original — e o `finance_data.json` gravado em disco
some junto. Isso não é um bug do seu código, é uma característica da hospedagem.

A solução é parar de gravar em arquivo e passar a gravar num banco de verdade.
Foi isso que eu fiz: o app agora pode salvar tudo no **Postgres do Supabase**
(gratuito no plano free), que é persistente de verdade.

## 2) Como migrar para o Supabase

**Passo 1 — Crie um projeto** em https://supabase.com (gratuito).

**Passo 2 — Rode o SQL**: abra o *SQL Editor* do projeto, cole o conteúdo do
arquivo `supabase_setup.sql` (incluído aqui) e clique em **RUN**. Esse script:
- cria a tabela `finance_data` (guarda todo o app em uma única linha JSON);
- cria a tabela `finance_data_backup` (usada pelos botões de backup/restore);
- já importa os dados que estavam no seu `finance_data.json` atual — nada se perde.

**Passo 3 — Pegue as credenciais**: em *Project Settings → API*, copie:
- `Project URL` → variável `SUPABASE_URL`
- `service_role` key (não é a `anon`!) → variável `SUPABASE_KEY`

**Passo 4 — Configure no Render**: no seu serviço, vá em *Environment* e adicione:
```
SUPABASE_URL = https://xxxxxxxx.supabase.co
SUPABASE_KEY = eyJ... (a service_role key)
```
Depois é só fazer o deploy (`git push` ou "Manual Deploy"). O app detecta essas
variáveis automaticamente e passa a ler/gravar no Supabase em vez do `.json` local.
Sem elas, ele continua funcionando normalmente com o arquivo local (bom para rodar
na sua máquina).

> **Importante**: a `service_role` key tem acesso total ao banco — trate-a como
> senha. Nunca a coloque no código do frontend, só como variável de ambiente do
> servidor (é assim que já está configurado).

## 3) Checklist mensal de contas

Nova aba **"Checklist do mês"** na barra lateral. Mostra todas as contas que
vencem no mês selecionado (respeitando parcelas/recorrência, igual ao resto do
app), com:
- navegação entre meses (setas);
- um anel de progresso e barra mostrando quanto já foi pago x quanto falta;
- clique na conta inteira para marcar/desmarcar como paga (não precisa clicar
  num botão pequeno);
- filtros "Todas / Pendentes / Pagas";
- uma comemoração rápida quando você fecha 100% das contas do mês.

Isso é independente do controle de parcelas que já existia (botão "✓" em
Contas) — o checklist é só "paguei esse mês, sim ou não", e reseta sozinho a
cada mês porque cada marcação é salva por (mês, conta).

## 4) Frontend

Adicionei animações e microinterações no app inteiro: transição suave ao trocar
de aba, cards com leve elevação ao passar o mouse, checkbox animado com "risco"
desenhado, anel de progresso animado, barra de progresso com transição suave,
e a comemoração ao concluir o mês. O visual (cores, fontes, layout) que você já
tinha foi mantido — só ficou mais vivo.

## Arquivos neste pacote
- `app.py` — backend + frontend atualizados
- `requirements.txt` — adicionado o pacote `supabase`
- `supabase_setup.sql` — script pronto para o SQL Editor do Supabase
- `finance_data.json` — mantido como fallback para rodar localmente sem Supabase
