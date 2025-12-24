# Решение проблемы Docker в Proxmox LXC

## Проблема

При попытке запуска Docker контейнеров в Proxmox LXC контейнере возникает ошибка:
```
Error response from daemon: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: open sysctl net.ipv4.ip_unprivileged_port_start file: reopen fd 8: permission denied
```

Это происходит потому, что непривилегированный LXC контейнер не позволяет Docker изменять системные параметры ядра (sysctl).

## Решение: Настройка LXC контейнера на Proxmox хосте

### Шаг 1: Подключиться к Proxmox хосту

```bash
ssh root@<proxmox_host_ip>
```

### Шаг 2: Найти ID вашего LXC контейнера

```bash
pct list | grep "Fin-Otdel"
# Или
pct list
```

Допустим ID контейнера: **101** (замените на свой)

### Шаг 3: Остановить контейнер

```bash
pct stop 101
```

### Шаг 4: Отредактировать конфигурацию контейнера

```bash
nano /etc/pve/lxc/101.conf
```

Добавьте следующие строки в конец файла:

```
# Разрешить Docker работать корректно
lxc.apparmor.profile: unconfined
lxc.cgroup.devices.allow: a
lxc.cap.drop:
lxc.mount.auto: proc:rw sys:rw

# Разрешить доступ к системным файлам
lxc.mount.entry: /dev/fuse dev/fuse none bind,create=file 0 0
```

**ИЛИ** (более безопасный вариант):

Просто сделайте контейнер привилегированным:

```bash
# В файле /etc/pve/lxc/101.conf
# Измените или добавьте:
unprivileged: 0
```

### Шаг 5: Запустить контейнер

```bash
pct start 101
```

### Шаг 6: Проверить

Подключитесь к контейнеру и попробуйте запустить Docker:

```bash
pct enter 101
cd /opt/west_rashod
docker compose -f docker-compose.prod.yml up -d
```

## Альтернатива: Использовать VM вместо LXC

Если изменение LXC контейнера нежелательно, создайте полноценную VM в Proxmox:

1. Создайте новую VM с Ubuntu 22.04
2. Установите Docker
3. Запустите деплой

VM не имеет ограничений LXC и Docker будет работать без проблем.

## Альтернатива 2: Деплой без Docker

См. файл [DEPLOYMENT_NO_DOCKER.md](DEPLOYMENT_NO_DOCKER.md) для инструкции по установке без Docker.

---

## Дополнительная информация

Подробнее о Docker в Proxmox:
- https://pve.proxmox.com/wiki/Linux_Container
- https://forum.proxmox.com/threads/docker-in-lxc.52301/
