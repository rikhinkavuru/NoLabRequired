-- ===========================================================================
--  No Lab Required -- component filter
--  Maps the book's authoring syntax onto the LaTeX component library
--  (tex/preamble.tex, spec B7) for PDF and onto semantic classes for HTML.
--  Runs post-quarto so executed-cell output is already in the AST.
-- ===========================================================================

local LATEX = FORMAT:match 'latex' or FORMAT:match 'beamer'

local function raw(s) return pandoc.RawBlock('latex', s) end
local function rawi(s) return pandoc.RawInline('latex', s) end

-- LaTeX-escape a plain string used inside an argument.
local function esc(s)
  if not s then return '' end
  return (s:gsub('([#%$%%&_{}])', '\\%1')
           :gsub('\\', '\\')
           :gsub('~', '\\textasciitilde{}')
           :gsub('%^', '\\textasciicircum{}'))
end

local function hasClass(el, c)
  return el.classes and el.classes:includes(c)
end

-- Terms encountered, dumped for the glossary-coverage check in tools/check_glossary.py
local seen_terms = {}

-- ---------------------------------------------------------------------------
-- Glossary links
--
-- Spec B9 asks for glossary terms to be hyperlinked. Each entry in the
-- glossary gets an anchor derived from the term, and each {.term} markup in the
-- chapters links to it. The slug is computed the same way on both sides, so the
-- two cannot drift apart.
local function gloss_anchor(term)
  local slug = term:lower():gsub("[^%w]+", "-"):gsub("^-+", ""):gsub("-+$", "")
  return "gloss-" .. slug
end

-- The glossary is recognised by its own H1, not by its filename: Quarto renders
-- through an intermediate file, so the source path is not visible here.
-- Finding the glossary is not as simple as it should be. The web edition
-- renders each chapter as its own document, where Quarto has already promoted
-- the H1 into doc.meta.title. The PDF renders the entire book as one merged
-- document, where the title is the book's and the glossary is a level-1 header
-- part way down. This handles both by tracking the most recent header and
-- falling back to the metadata title.
local function glossary_title(inlines)
  return pandoc.utils.stringify(inlines):lower():match("glossary") ~= nil
end

local function meta_is_glossary(doc)
  return doc.meta and doc.meta.title
    and pandoc.utils.stringify(doc.meta.title):lower():match("glossary") ~= nil
end

local function anchor_glossary(doc)
  local in_glossary = meta_is_glossary(doc)
  local out = pandoc.List()

  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" and block.level <= 1 then
      in_glossary = glossary_title(block.content)
      out:insert(block)
    elseif block.t == "DefinitionList" and in_glossary then
      if LATEX then
        -- Rebuilt rather than annotated. LaTeX's description environment hangs
        -- the term into the margin, outside the text block, and it is handled
        -- by the block package so its layout keys cannot be reconfigured.
        for _, item in ipairs(block.content) do
          local term = pandoc.utils.stringify(item[1])
          out:insert(raw("\\nlrglossterm{\\label{" .. gloss_anchor(term) .. "}"
            .. esc(term) .. "}"))
          out:insert(raw("\\begin{nlrglossdef}"))
          for _, defn in ipairs(item[2]) do
            for _, b in ipairs(defn) do out:insert(b) end
          end
          out:insert(raw("\\end{nlrglossdef}"))
        end
      else
        for _, item in ipairs(block.content) do
          local term = pandoc.utils.stringify(item[1])
          if term ~= "" then
            -- Wrap the term rather than inserting an empty span beside it.
            -- Pandoc drops an empty span, which left all 62 glossary links in
            -- the web edition pointing at nothing.
            item[1] = { pandoc.Span(item[1],
              pandoc.Attr(gloss_anchor(term), {"nlr-gloss-anchor"}, {})) }
          end
        end
        out:insert(block)
      end
    else
      out:insert(block)
    end
  end
  doc.blocks = out
end

-- ---------------------------------------------------------------------------
-- Cross-references
--
-- Spec B9 asks for cross-references to be hyperlinked. The book says "Chapter
-- 12" 250-odd times in running prose, and a reader on a screen should be able
-- to go there. Each chapter's H1 gets an anchor, and each mention in prose
-- becomes a link to it.
--
-- The mention is rewritten only when it is followed by something that is not a
-- digit, so "Chapter 1" inside "Chapter 12" is never matched, and only in
-- prose, never inside code.
local CHAPTER_MENTION = "^Chapter$"

local function chapter_anchor(n)
  return "nlrch-" .. n
end

-- The chapter number comes from the source filename, chNN-slug.qmd, which is
-- the only place it is stated once. Heading text does not carry it and the
-- counter is not available to a filter.
local function this_chapter()
  local files = PANDOC_STATE and PANDOC_STATE.input_files or {}
  for _, f in ipairs(files) do
    local n = f:match("ch(%d%d)[%-_]")
    if n then return tostring(tonumber(n)) end
  end
  return nil
end

-- Rewrites a Str "Chapter" followed by Space and a numeric Str.
function Inlines(inlines)
  local out = pandoc.List()
  local i = 1
  while i <= #inlines do
    local a, b, c = inlines[i], inlines[i + 1], inlines[i + 2]
    local is_ref = a and a.t == "Str" and a.text:match(CHAPTER_MENTION)
      and b and b.t == "Space"
      and c and c.t == "Str" and c.text:match("^%d+")
    if is_ref then
      local num = c.text:match("^(%d+)")
      local tail = c.text:sub(#num + 1)
      local label = pandoc.Str("Chapter " .. num)
      if LATEX then
        out:insert(rawi("\\hyperref[" .. chapter_anchor(num) .. "]{Chapter " .. num .. "}"))
      else
        out:insert(pandoc.Link({label}, "#" .. chapter_anchor(num)))
      end
      if tail ~= "" then out:insert(pandoc.Str(tail)) end
      i = i + 3
    else
      out:insert(a)
      i = i + 1
    end
  end
  return out
end

-- ---------------------------------------------------------------------------
-- Inline code: allow it to break.
--
-- A token like NM_007294.4(BRCA1):c.68_69del is 29 unbreakable characters, and
-- on a 4.60 in measure TeX has nowhere to put it, so it hangs half an inch past
-- the text block. Accession numbers, HGVS strings and file paths all look like
-- this. Breaks are offered after the separators a reader already reads as
-- boundaries, and nowhere else, so a name never splits mid-word.
local BREAK_AFTER = { ["."] = true, ["_"] = true, [":"] = true, ["/"] = true,
                      ["("] = true, [")"] = true, ["-"] = true, [","] = true,
                      ["="] = true, ["|"] = true }

-- Single characters only; the caller walks the string one character at a time.
-- \char forms rather than \textasciicircum and friends, because those live in
-- the TS1 encoding and JetBrains Mono NL ships no TS1 font definition, so they
-- fail at build time. And a bare backslash has to be caught here: `\t` in
-- inline code otherwise reaches LaTeX as \t, which is the tie-after accent,
-- and the error it raises names neither the file nor the chapter.
local CODE_ESCAPE = {
  ["\\"] = "\\char92{}",
  ["{"]  = "\\char123{}",
  ["}"]  = "\\char125{}",
  ["~"]  = "\\char126{}",
  ["^"]  = "\\char94{}",
  ["&"]  = "\\&",
  ["%"]  = "\\%",
  ["$"]  = "\\$",
  ["#"]  = "\\#",
  ["_"]  = "\\_",
}

local function escape_code(ch)
  return CODE_ESCAPE[ch] or ch
end

function Code(el)
  if not LATEX then return nil end
  local out = {}
  local n = #el.text
  for i = 1, n do
    local ch = el.text:sub(i, i)
    table.insert(out, escape_code(ch))
    -- No break after the final character, and none before a closing bracket.
    if BREAK_AFTER[ch] and i < n then
      table.insert(out, "\\nlrbreak{}")
    end
  end
  return rawi("\\texttt{" .. table.concat(out) .. "}")
end

-- ---------------------------------------------------------------------------
-- Inline: key terms and margin notes
-- ---------------------------------------------------------------------------
function Span(el)
  if hasClass(el, 'term') then
    local definition = el.attributes['def']
    local label = pandoc.utils.stringify(el.content)
    seen_terms[label] = definition or ''
    if LATEX then
      -- The bold term links to its glossary entry.
      local linked = rawi('\\hyperref[' .. gloss_anchor(label) .. ']{\\textbf{'
        .. esc(label) .. '}}')
      if definition and definition ~= '' then
        return { rawi('\\nlrdeflinked{'), linked, rawi('}{' .. esc(definition) .. '}') }
      end
      return linked
    end
    -- HTML: the definition has to be visible here too, or the web edition
    -- silently loses every margin definition in the book. The term links to
    -- its glossary entry, same as in print.
    local out = pandoc.List({
      pandoc.Span(
        { pandoc.Link(el.content, '#' .. gloss_anchor(label)) },
        pandoc.Attr('', {'nlr-term'}, {{'data-term', label}})),
    })
    if definition and definition ~= '' then
      out:insert(pandoc.Span(
        { pandoc.Str(definition) },
        pandoc.Attr('', {'nlr-term-def'}, {})
      ))
    end
    return out
  end

  if hasClass(el, 'margin') then
    if LATEX then
      return { rawi('\\nlrnote{'), pandoc.Span(el.content), rawi('}') }
    end
    return pandoc.Span(el.content, pandoc.Attr('', {'nlr-margin'}, {}))
  end

  return nil
end

-- ---------------------------------------------------------------------------
-- Code blocks and executed output
-- ---------------------------------------------------------------------------
local function isOutputBlock(el)
  return hasClass(el, 'output')
      or hasClass(el, 'cell-output')
      or hasClass(el, 'cell-output-stdout')
      or hasClass(el, 'cell-output-stderr')
end

function CodeBlock(el)
  if not LATEX then
    -- HTML: annotate so the SCSS can draw the filename chip and the OUTPUT rule.
    if el.attributes['filename'] then el.classes:insert('nlr-code') end
    if isOutputBlock(el) then el.classes:insert('nlr-output') end
    return el
  end

  if isOutputBlock(el) then
    return {
      raw('\\begin{nlroutputbox}'),
      pandoc.CodeBlock(el.text, pandoc.Attr('', {'default'}, {})),
      raw('\\end{nlroutputbox}'),
    }
  end

  local fname = el.attributes['filename'] or ''
  return {
    raw('\\begin{nlrcodebox}{' .. esc(fname) .. '}'),
    el,
    raw('\\end{nlrcodebox}'),
  }
end

-- ---------------------------------------------------------------------------
-- Block components
-- ---------------------------------------------------------------------------
local FIELD_LABEL = {
  goal    = 'Goal',
  given   = 'Given',
  produce = "You'll produce",
  check   = 'Check your work',
}

-- Closed callout taxonomy. Five labels, no Note/Tip/Info/Warning zoo: a reader
-- should not have to memorise a legend before they can read the page.
local SIMPLE_BOXES = {
  ifbreaks = { env = 'nlrbreaks', class = 'nlr-ifbreaks' },
  trap     = { env = 'nlrtrap',   class = 'nlr-trap' },
  check    = { env = 'nlrcheck',  class = 'nlr-check' },
  why      = { env = 'nlrwhy',    class = 'nlr-why' },
}

local function wrap(el, open, close)
  local out = pandoc.List()
  out:insert(raw(open))
  out:extend(el.content)
  out:insert(raw(close))
  return out
end

function Div(el)
  -- ---- exercise ----------------------------------------------------------
  if hasClass(el, 'exercise') then
    local num  = el.attributes['num'] or ''
    local time = el.attributes['time'] or ''
    if LATEX then
      return wrap(el,
        '\\begin{nlrexercise}{Exercise ' .. esc(num) .. '}{' .. esc(time) .. '}',
        '\\end{nlrexercise}')
    end
    local head = pandoc.Div(
      { pandoc.Plain{ pandoc.Span({pandoc.Str('Exercise'), pandoc.Space(), pandoc.Str(num)}, pandoc.Attr('', {'nlr-ex-num'})),
                      pandoc.Span({pandoc.Str(time)}, pandoc.Attr('', {'nlr-ex-time'})) } },
      pandoc.Attr('', {'nlr-ex-head'}))
    local content = pandoc.List({head})
    content:extend(el.content)
    return pandoc.Div(content, pandoc.Attr(el.identifier, {'nlr-exercise'}, {}))
  end

  -- ---- exercise sub-fields ----------------------------------------------
  for key, label in pairs(FIELD_LABEL) do
    if hasClass(el, key) then
      if LATEX then
        return wrap(el, '\\nlrfield{' .. label .. '}', '')
      end
      local content = pandoc.List({
        pandoc.Plain{ pandoc.Span({pandoc.Str(label)}, pandoc.Attr('', {'nlr-field-label'})) } })
      content:extend(el.content)
      return pandoc.Div(content, pandoc.Attr('', {'nlr-field', 'nlr-field-' .. key}, {}))
    end
  end

  -- ---- the four boxed callouts ------------------------------------------
  for name, spec in pairs(SIMPLE_BOXES) do
    if hasClass(el, name) then
      if LATEX then
        return wrap(el, '\\begin{' .. spec.env .. '}', '\\end{' .. spec.env .. '}')
      end
      return pandoc.Div(el.content, pandoc.Attr(el.identifier, {spec.class}, {}))
    end
  end

  -- ---- version pin -------------------------------------------------------
  if hasClass(el, 'asof') then
    if LATEX then
      return wrap(el, '\\nlrasof{', '}')
    end
    local content = pandoc.List({
      pandoc.Plain{ pandoc.Span({pandoc.Str('As of')}, pandoc.Attr('', {'nlr-asof-label'})) } })
    content:extend(el.content)
    return pandoc.Div(content, pandoc.Attr('', {'nlr-asof'}, {}))
  end

  -- One error/fix pair inside an .ifbreaks box. Each one gets a stable anchor
  -- derived from the error text so the generated error index at the back can
  -- point at a real page number rather than at a chapter.
  if hasClass(el, 'errfix') then
    local err = el.attributes['err'] or ''
    local slug = err:lower():gsub('[^%w]+', '-'):gsub('^-+', ''):gsub('-+$', ''):sub(1, 60)
    if slug == '' then slug = 'unnamed' end
    local anchor = 'err-' .. slug

    local out = io.open(os.getenv('NLR_ERRORS_OUT') or '/dev/null', 'a')
    if out then
      out:write(string.format('%s\t%s\n', anchor, err))
      out:close()
    end

    if LATEX then
      return {
        raw('\\nlrerrfix{' .. esc(err) .. '}{\\label{' .. anchor .. '}'),
        pandoc.Div(el.content),
        raw('}'),
      }
    end
    local content = pandoc.List({
      pandoc.Plain{ pandoc.Code(err) } })
    content:extend(el.content)
    return pandoc.Div(content, pandoc.Attr(anchor, {'nlr-errfix'}, {}))
  end

  -- ---- generic labelled note --------------------------------------------
  if hasClass(el, 'notebox') then
    local label = el.attributes['label'] or 'Note'
    if LATEX then
      return wrap(el, '\\begin{nlrnotebox}{' .. esc(label) .. '}', '\\end{nlrnotebox}')
    end
    local content = pandoc.List({
      pandoc.Plain{ pandoc.Span({pandoc.Str(label)}, pandoc.Attr('', {'nlr-note-label'})) } })
    content:extend(el.content)
    return pandoc.Div(content, pandoc.Attr('', {'nlr-notebox'}, {}))
  end

  -- ---- checkpoint --------------------------------------------------------
  if hasClass(el, 'checkpoint') then
    if LATEX then
      -- Body is expected to be a single bullet list; unwrap it so the
      -- environment supplies the itemize.
      local items = pandoc.List()
      for _, blk in ipairs(el.content) do
        if blk.t == 'BulletList' then
          for _, item in ipairs(blk.content) do
            items:insert(raw('\\item '))
            items:extend(item)
          end
        else
          items:insert(blk)
        end
      end
      local out = pandoc.List({ raw('\\begin{nlrcheckpoint}') })
      out:extend(items)
      out:insert(raw('\\end{nlrcheckpoint}'))
      return out
    end
    local content = pandoc.List({
      pandoc.Plain{ pandoc.Span({pandoc.Str('You should now be able to')}, pandoc.Attr('', {'nlr-cp-label'})) } })
    content:extend(el.content)
    return pandoc.Div(content, pandoc.Attr(el.identifier, {'nlr-checkpoint'}, {}))
  end

  -- ---- answer space ------------------------------------------------------
  if hasClass(el, 'answerspace') then
    local lines = el.attributes['lines'] or '4'
    if LATEX then
      return raw('\\nlranswerlines{' .. lines .. '}')
    end
    return pandoc.Div({}, pandoc.Attr('', {'nlr-answerspace'}, {{'data-lines', lines}}))
  end

  if hasClass(el, 'answerbox') then
    local height = el.attributes['height'] or '1.6in'
    if LATEX then
      return raw('\\nlranswerbox{' .. height .. '}')
    end
    return pandoc.Div({}, pandoc.Attr('', {'nlr-answerbox'}, {{'style', 'height:' .. height}}))
  end

  -- ---- full-bleed passthrough -------------------------------------------
  if hasClass(el, 'fullwidth') then
    if LATEX then
      return wrap(el, '\\begin{nlrfull}', '\\end{nlrfull}')
    end
    return el
  end

  return nil
end

-- ---------------------------------------------------------------------------
-- Dump the terms this document marked up, for the glossary-coverage check.
-- ---------------------------------------------------------------------------
function Pandoc(doc)
  anchor_glossary(doc)

  -- Anchor this chapter so every "Chapter N" elsewhere in the book can link to
  -- it. Placed immediately after the H1 so the jump lands on the title.
  local n = this_chapter()
  if n then
    for i, block in ipairs(doc.blocks) do
      if block.t == "Header" and block.level == 1 then
        local anchor = chapter_anchor(n)
        if LATEX then
          table.insert(doc.blocks, i + 1, raw("\\label{" .. anchor .. "}"))
        else
          table.insert(doc.blocks, i + 1,
            pandoc.Div({}, pandoc.Attr(anchor, {"nlr-anchor"}, {})))
        end
        break
      end
    end
  end

  local out = os.getenv('NLR_TERMS_OUT')
  if out then
    local f = io.open(out, 'a')
    if f then
      for term, def in pairs(seen_terms) do
        f:write(string.format('%s\t%s\n', term, def:gsub('\t', ' ')))
      end
      f:close()
    end
  end
  return doc
end
