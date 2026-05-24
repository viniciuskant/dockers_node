
# Projeto envio de dados via MQTT com Dockers

Comunicação entre os containers

Esse projeto usa dois containers Docker que trabalham juntos e se comunicam pela rede interna iot_network.

- O primeiro container é o `simulator`, responsável por gerar os dados falsos dos sensores, como temperatura, umidade, co2, so2 e outros.
- O segundo é o `mqtt-sender`, responsável por receber esses dados do simulador e fazer o envio para o broker MQTT usando conexão segura com certificados mTLS.

A comunicação acontece porque os dois containers estão na mesma rede Docker (bridge), permitindo que o simulador encontre o sender. Essa separação foi feita para deixar a arquitetura mais organizada e mais próxima de um ambiente IoT real. Assim, o container de simulação pode ser removido facilmente e substituído por sensores físicos reais, sem precisar alterar a parte responsável pelo envio MQTT.


## Como estão relacionados

`simulator -> mqtt-sender -> Mosquitto (broker/server)`

### Fluxo principal

### Fluxo principal

O funcionamento da arquitetura acontece em etapas:

- O simulator gera os dados falsos dos sensores IoT.
- Esses dados são enviados via socket TCP para o container mqtt-sender.
- O mqtt-sender recebe as mensagens e faz o envio para o Broker MQTT (Mosquitto) usando conexão segura com mTLS.

Essa separação deixa o sistema mais organizado e facilita substituir futuramente o simulador por sensores físicos reais.

### Mecanismo de fallback (SQLite)

O sistema possui um mecanismo de tolerância a falhas para evitar perda de mensagens caso o Broker fique offline.

Como funciona
- Se o Broker MQTT estiver indisponível:
    - As mensagens são armazenadas localmente em um banco SQLite3.
    - O arquivo fica salvo em `/app/data/pending_messages.db`

- Quando a conexão com o Broker volta:
    - O mqtt-sender tenta reenviar automaticamente todas as mensagens pendentes.
    - Após o envio com sucesso, as mensagens são marcadas como enviadas no banco.

Esse mecanismo garante maior confiabilidade no envio dos dados IoT, evitando perda de informações durante falhas de rede, reinicializações do broker ou instabilidades temporárias. Note que enquanto o método `flush_pending()` está reenviando as mensagens armazenadas no SQLite, o mqtt-sender ainda continua recebendo novas mensagens da simulação. Como o envio de dados esperado para essa aplicação é baixo, essa estrutura se torna eficiente.

---

## Geração de certificados

O script Python usa criptografia **mTLS**. Por isso, o container **Só vai funcionar** se os certificados deste node estiverem gerados e guardados na raiz da `certs/`, para segurança é recomendado que eles estejam com as permissões apenas de leitura:

* `certs/ca.crt` (Permissão: 400)
* `certs/cliente.crt` (Permissão: 400)
* `certs/cliente.key` (Permissão: 400)

Um script para gerar esse certificados pode se encontrado nesse [repositório](https://github.com/viniciuskant/dockers_server/blob/main/scripts/deploy_nodes.sh), esse repositório é onde está cofigurado o servidor para esssa aplicação.

---

## Como fazer o Build

```bash
docker-compose up --build -d
```


## Objetivo da arquitetura

O objetivo é simular o mais próximo possível de um ambiente IoT real:

    - Cada máquina ou container representa um dispositivo físico
    - Em ambiente local, o sistema detecta automaticamente o hardware real

Isso permite que os dados enviados pareçam vir de sensores reais distribuídos em diferentes dispositivos.


## Funcionamento do script `install.sh`
O script install.sh é usado para atualizar e implantar os containers Docker do projeto (mqtt-sender e simulator), com mecanismos de backup e rollback para garantir alta disponibilidade.

Fluxo:
1. Lê as variáveis (ex.: VERSION_DOCKER) do arquivo .env que está em /tmp/update_docker_temp/extract.
2. Cria um backup da versão atual (em $HOME/dockers_node) para $HOME/history/last.
3. Remove o diretório ativo e copia os novos arquivos (código-fonte, docker-compose, etc.) do diretório temporário para $HOME/dockers_node.
4. Copia os certificados mTLS (ca.crt, cliente.crt, cliente.key) da home do usuário para $HOME/dockers_node/certs/.
5. Marca que rollback pode ser necessário (ROLLBACK_NEEDED=true), derruba containers antigos e sobe os novos com docker-compose up -d.
6. Valida se os containers estão rodando (verifica nomes com HOSTNAME e VERSION_DOCKER).
7. Se tudo ok, desativa rollback e encerra com sucesso.


Rollback:
- Se qualquer comando falhar (set -e), a função rollback é chamada.
- O rollback restaura os arquivos do último backup ($HOME/history/last) e reinicia os containers com docker-compose up -d --build.
- O rollback só é executado se ROLLBACK_NEEDED=true (ou seja, após o início da substituição).

Pré-requisitos:
- Diretório /tmp/update_docker_temp/extract com .env e todos os arquivos da aplicação.
- Certificados na home do usuário ($HOME/ca.crt, $HOME/cliente.crt, $HOME/cliente.key).
- Docker e Docker Compose instalados.

Os quais são de responsabilidade do [repositório](https://github.com/viniciuskant/dockers_server) fazer, pois ele que cria os pacotes de versões e faz o gerenciamento de quem deve ser atualizado, é responsável pelo scritp de `update_node.sh` que é responsável por executar o install.

OBSERVAÇÕES:
- O script usa set -e para abortar em erro.
- Os nomes dos containers incluem HOSTNAME e VERSION_DOCKER.
- A comunicação entre containers depende da rede iot_network definida no docker-compose.yml.

## Resultado esperado

Cada instância do simulador representa um dispositivo IoT enviando dados de sensores (temperatura, umidade, CO2, etc.) para um broker MQTT, simulando um ambiente distribuído real.
text

