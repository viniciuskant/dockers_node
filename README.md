# MQTT Sensor Simulator

Simulador de dispositivos IoT que envia dados de sensores via MQTT.

## Build e execução

```bash
docker build -t mqtt-simulator .

docker run -d \
  --name mqtt-simulator-$(hostname) \
  --restart unless-stopped \
  -e DEVICE_MAC=$(cat /sys/class/net/eth0/address) \
  mqtt-simulator
```

## Parar e remover container
```bash
docker stop mqtt-simulator-$(hostname)
docker rm mqtt-simulator-$(hostname)
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

