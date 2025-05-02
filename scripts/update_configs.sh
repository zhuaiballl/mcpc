#!/bin/zsh
# 自动检测新配置文件并验证格式
find config/ -name "*.yaml" | xargs -n1 yamllint