#!/bin/zsh

if [[ "$1" == "--no-color" ]]; then
    shift
    nocolor="nocolor"
fi

if [[ "$nocolor" != "nocolor" ]] && [ -t 2 ]; then
    BOLD="\e[1m"
    ERROR="\e[1;31m"
    WARNING="\e[1;38;5;208m"
    SUCCESS="\e[1;32m"
    INFO="\e[1;34m"
    RESET="\e[0m"
else
    BOLD=""
    ERROR=""
    WARNING=""
    SUCCESS=""
    INFO=""
    RESET=""
fi

log() {
    eval "STYLE=\"\${$1}\""
    print -u 2 "${STYLE}$1: $2${RESET}"
}

FIGURES=(
    account-countries-2023 account-countries
    capita-countries
    comparable-reports meta platforms reports-best
)

prepare_figures() {
    for name in $FIGURES; do
        rsvg-convert -f pdf -o "figure-${name}.pdf" "../figure/${name}.svg"
    done
}

check_bibtex() {
    # Surface actionable information from BibTeX's output
    local warnings=$(
        grep -e '^Warning--' "$1.blg" |
        grep -ve 'no number and no volume' |
        grep -ve 'page numbers missing' |
        grep -ve 'can'"'"'t use both author and editor fields')

    if [[ -n $warnings ]]; then
        log ERROR "Please fix the following BibTeX warnings:\n$warnings"
        exit 1
    fi
}

check_latex() {
    # Surface actionable information from LaTeX's output
    local warnings=$(
        grep -e '^LaTeX Warning: Reference `' "$1.log")

    if [[ -n $warnings ]]; then
        log ERROR "Please fix the following LaTeX warnings:\n$warnings"
        exit 1
    fi

    local errors=$(
        grep -e '^! LaTeX Error:' "$1.log" |
        sed -e 's/\\/\\\\/g')

    if [[ -n $errors ]]; then
        log ERROR "Please fix the following LaTeX errors:\n$errors"
        exit 1
    fi
}

local LATEX_ENGINE=pdflatex

do_build() {
    log INFO "$LATEX_ENGINE $1"
    $LATEX_ENGINE -interaction=batchmode "$1"

    log INFO "bibtex $1"
    bibtex -terse "$1"
    check_bibtex "$1"

    log INFO "$LATEX_ENGINE $1"
    $LATEX_ENGINE -interaction=batchmode "$1"
    while ( grep -q '^LaTeX Warning: Label(s) may have changed' "$1.log" ); do
        log INFO "$LATEX_ENGINE $1"
        $LATEX_ENGINE -interaction=batchmode "$1"
    done

    check_latex "$1"
}

do_wordcount() {
    pandoc report.tex -f latex --quiet -t plain -s -o report.txt
    local WITHOUT_REFS="$(wc -w report.txt | cut -wf 1-2 | xargs)"
    pandoc report.tex -f latex --quiet -C --bibliography=bibliography.bib -t plain -s -o report.txt
    local WITH_REFS="$(wc -w report.txt | cut -wf 1-2 | xargs)"
    log INFO "$WITHOUT_REFS words without, $WITH_REFS words with references"
}

prep_arxiv() {
    # Make sure working directory exists.
    [ ! -d ../arxiv ] && mkdir ../arxiv

    # Combine all LaTeX sources into one.
    log INFO "Stage arxiv"
    latexpand report.tex -o ../arxiv/report.tex || exit "$?"

    # Include the bibliography.
    cp report.bbl ../arxiv/report.bbl
    cp figure-*.pdf ../arxiv/

    # Package it all up
    log INFO "Create archive"
    (cd .. && zip -r arxiv.zip arxiv/*)

    # Make sure the paper still builds.
    log INFO "Build archive version"
    unset TEXINPUTS
    (cd ../arxiv && pdflatex report) || exit "$?"
    (cd ../arxiv && pdflatex report) || exit "$?"
    (cd ../arxiv && pdflatex report) || exit "$?"
}

target=${1:-report}
if [ $# -ne 0 ]; then
    shift
fi

case $target in
    figure )
        prepare_figures
        ;;
    report )
        do_build report
        ;;
    wordcount )
        do_wordcount
        ;;
    arxiv )
        prep_arxiv
        ;;
    *     )
        log ERROR "\"$target\" is not a valid build target!"
        exit 1
        ;;
esac
