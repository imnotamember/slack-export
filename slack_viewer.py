from sys import argv
import slackviewer.main as slack

path = argv[1:]
vamp_lab = slack.main(archive=path)
pass
