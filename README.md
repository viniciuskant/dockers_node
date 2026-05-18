
# Guia  MQTT Simulator Node

Anotações rápidas de como buildar, rodar e derrubar o container de simulação de sensores nos nodes.

---

## Requisitos antes de começar

O script Python usa criptografia **mTLS**. Por isso, o container **Só vai funcionar** se os certificados deste node estiverem gerados e guardados na raiz da `certs/` com as permissões apenas de leitura:

* `certs/ca.crt` (Permissão: 400)
* `certs/cliente.crt` (Permissão: 400)
* `certs/cliente.key` (Permissão: 400)


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

