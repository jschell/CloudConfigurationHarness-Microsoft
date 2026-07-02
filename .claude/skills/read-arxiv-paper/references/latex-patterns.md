# LaTeX Patterns for Paper Reading

Common patterns in arXiv paper LaTeX source.

## Document Structure

```latex
\documentclass{article}  % Entry point indicator

\begin{document}

\title{Paper Title}
\author{Author Names}
\maketitle

\begin{abstract}
Abstract text here
\end{abstract}

\section{Introduction}
\section{Related Work}
\section{Method}
\section{Experiments}
\section{Conclusion}

\bibliography{refs}
\end{document}
```

## File Includes

**Follow these:**
```latex
\input{sections/intro}      % Inserts content (no .tex needed)
\input{sections/intro.tex}  % Explicit extension
\include{chapter1}          % Inserts with page break
```

**Skip these:**
```latex
\bibliography{references}   % Just a citation database
\bibliographystyle{plain}   % Style file
\usepackage{custom}         % Package/style
```

## Extracting Content

### Title & Authors
```latex
\title{...}
\author{...}
% Or in some templates:
\Author{...}
\Title{...}
```

### Abstract
```latex
\begin{abstract}
...
\end{abstract}
```

### Sections
```latex
\section{Name}          % Level 1
\subsection{Name}       % Level 2
\subsubsection{Name}    % Level 3
\paragraph{Name}        % Level 4
```

### Figures
```latex
\begin{figure}
  \includegraphics{image.pdf}
  \caption{Description}
  \label{fig:name}
\end{figure}
```

### Tables
```latex
\begin{table}
  \begin{tabular}{|c|c|}
    ...
  \end{tabular}
  \caption{Description}
\end{table}
```

### Equations
```latex
\begin{equation}
  E = mc^2
  \label{eq:einstein}
\end{equation}

% Inline: $E = mc^2$
% Display: $$E = mc^2$$ or \[ E = mc^2 \]
```

## Common Templates

### NeurIPS/ICML
```
main.tex
neurips_2024.sty    # Skip
sections/
  intro.tex
  method.tex
  experiments.tex
```

### arXiv Default
```
paper.tex           # Single file common
figures/
references.bib
```

### ACL/EMNLP
```
acl2024.tex
acl.sty             # Skip
anthology.bib
```

## Cleaning LaTeX

**Remove for readability:**
- `\cite{...}` → [citation]
- `\ref{...}` → [ref]
- `\label{...}` → (delete)
- `%.*$` → (comments)
- `\vspace{...}`, `\hspace{...}` → (delete)

**Keep important:**
- `\textbf{...}` → **bold**
- `\textit{...}` → *italic*
- `\emph{...}` → *emphasis*
- `$...$` → math (keep or render)

## Reading Order

1. **Abstract** - Get overview
2. **Introduction** - Problem and contributions
3. **Conclusion** - Summary and takeaways
4. **Method/Approach** - Technical details
5. **Experiments** - Validation
6. **Related Work** - Context (often less critical)
