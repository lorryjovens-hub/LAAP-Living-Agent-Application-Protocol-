@'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$scriptDir\laap\api\cli.py" @args
'@
