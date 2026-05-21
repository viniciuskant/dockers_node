
# Projeto envio de dados via MQTT com Dockers

Comunicação entre os containers

Esse projeto usa dois containers Docker que trabalham juntos e se comunicam pela rede interna iot_network.

- O primeiro container é o `simulator`, responsável por gerar os dados falsos dos sensores, como temperatura, umidade, co2, so2 e outros.
- O segundo é o `mqtt-sender`, responsável por receber esses dados do simulador e fazer o envio para o broker MQTT usando conexão segura com certificados mTLS.

A comunicação acontece porque os dois containers estão na mesma rede Docker (bridge), permitindo que o simulador encontre o sender. Essa separação foi feita para deixar a arquitetura mais organizada e mais próxima de um ambiente IoT real. Assim, o container de simulação pode ser removido facilmente e substituído por sensores físicos reais, sem precisar alterar a parte responsável pelo envio MQTT.


## Como estão relacionados

`simulator -> mqtt-sender -> Mosquitto (broker/server)`

### Fluxo principal

### Mecanismo de fallback (InfluxDB)

O sistema possui um mecanismo de tolerância a falhas para a queda do Broker:

* Em caso de indisponibilidade do Broker, as mensagens são armazenadas localmente em um banco SQLite3.
* Assim que a conexão com o Broker é restabelecida:
  - o sistema entra em um loop por tempo determinado reenviando as mensgens, assim que o tempo acaba ele
* Esse processo garante não perda de dados durante falhas ou instabilidades


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

Se alterar o código do `sim_node.py` ou o `Dockerfile`, precisa rebuildar a imagem dentro da pasta `dockers_node/`:

```bash
docker build -t mqtt-simulator .
```

## Como rodar

Comando oficial para subir o container puxando o hostname real, o MAC Address da placa eth0 e mapeando de forma segura os certificados que estão na Home do Linux:


```bash
docker run -d \
  --name mqtt-simulator-$(hostname) \
  --restart unless-stopped \
  -e DEVICE_MAC=$(cat /sys/class/net/eth0/address) \
  mqtt-simulator
```

## Como parar

Como estamos rodando o Docker puro (sem Compose), para derrubar e apagar o container use o rm -f:

```bash
docker rm -f mqtt-simulator-$(hostname)
```

## Comandos Úteis de Monitoramento

Ver se o container está de pé:

```bash
docker ps
```

Olhar os Logs (Ver se o mTLS conectou na porta 8883):

```bash
docker logs mqtt-simulator-$(hostname)
```

Ver o consumo de memória/CPU do container:

```bash
docker stats mqtt-simulator-$(hostname)
```

## Como funciona o MAC do dispositivo

O simulador define o identificador do dispositivo assim:

    - Se estiver rodando em Docker → usa DEVICE_MAC (passado do host)
    - Se estiver rodando direto na máquina → usa o MAC real da interface de rede (/sys/class/net/...)

## Objetivo da arquitetura

O objetivo é simular o mais próximo possível de um ambiente IoT real:

    - Cada máquina ou container representa um dispositivo físico
    - O MAC funciona como identificador único do device
    - Em Docker, o MAC do host é repassado para manter consistência
    - Em ambiente local, o sistema detecta automaticamente o hardware real

Isso permite que os dados enviados pareçam vir de sensores reais distribuídos em diferentes dispositivos.

## Resultado esperado

Cada instância do simulador representa um dispositivo IoT enviando dados de sensores (temperatura, umidade, CO2, etc.) para um broker MQTT, simulando um ambiente distribuído real.
text

