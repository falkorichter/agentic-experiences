# github copilot web 
* https://github.com/skend/export-tabs-urls/pull/1 has links to two agentic sessions
* super interesting to see this work in the browser
* prompt at https://github.com/copilot/share/820d430c-4800-8c23-b141-8048a4c10918

# build your own agent
* https://github.com/agno-agi/agno?tab=readme-ov-file
* https://docs.phidata.com/introduction
* https://www.langchain.com/ was also mentioned
   * https://github.com/HariDarshan2321/simple-agent
   * https://github.com/HariDarshan2321/leetcode-agent

# apple photos random

* https://claude.ai/share/fabaa70d-f078-401b-8eff-fefc5d9af99e
* input https://discussions.apple.com/thread/254813403?sortBy=rank

```
-- Fisher-Yates shuffle function
on fisherYatesShuffle(inputList)
	set shuffledList to inputList as list
	set listLength to count of shuffledList
	
	repeat with i from listLength to 2 by -1
		set randomIndex to (random number from 1 to i)
		
		-- Swap items at positions i and randomIndex
		set tempItem to item i of shuffledList
		set item i of shuffledList to item randomIndex of shuffledList
		set item randomIndex of shuffledList to tempItem
	end repeat
	
	return shuffledList
end fisherYatesShuffle

-- Usage in your photo script:
on getCurrentSelection()
	tell application "Photos"
		set imageSel to {}
		try
			set imageSel to (get selection)
		on error errTexttwo number errNumtwo
			display dialog ¬
				"Cannot get the selection: " & errNumtwo ¬
				& return & errTexttwo
		end try
		return imageSel
	end tell
end getCurrentSelection

set thephotos to getCurrentSelection()
set showslide_duration to 2

tell application "Photos"
	-- Single, proper shuffle instead of 3 imperfect ones
	display notification "beginning to shuffle" & (count of thephotos)
	set thephotos to my fisherYatesShuffle(thephotos)
	display notification "done to shuffle" & (count of thephotos)
	
	display notification "Shuffled " & (count of thephotos) & " photos" with title "Photos"
	
	start slideshow using thephotos as list
end tell
```

# Other use case

| I need a shell script (zsh) which renames all the files in a folder into a random new order when ordered by name. It's for photos and I want to run a random slideshow.

```
This script will:

Take a directory path as an argument (uses current directory if none provided)
Find all files in the directory (excluding subdirectories and hidden files)
Generate a random order using the Fisher-Yates shuffle algorithm
Rename files with zero-padded numbers (001.jpg, 002.png, etc.) so they sort in the new random order
Preserve file extensions so your photos remain viewable
Use safe renaming via a temporary directory to avoid conflicts
```

https://claude.ai/public/artifacts/05dcf788-b7b7-400c-a268-830fd4eca495 

```
The script preserves file extensions and uses zero-padded numbering (001, 002, 003...) so when your slideshow software sorts by filename, it will display the photos in the randomized order. The zero-padding ensures proper alphabetical sorting regardless of how many files you have.
```


```
there is an error random_rename_script.sh: line 68: %0${#${#actual_files[@]}}d%s: bad substitution
```

Edit
You're right, that's a complex substitution that zsh is having trouble with. Let me fix that by calculating the padding width separately:


Random File Renamer Script
Code ∙ Version 2 
The issue was with the nested substitution ${#${#actual_files[@]}} inside the printf format string. Now it calculates the padding width in a separate step, which should work reliably in zsh.

here is the output

Edit
I don't see the output you mentioned - could you paste it so I can see what error or issue you're encountering? That will help me diagnose and fix the problem with the script.

```
random_rename_script.sh: line 19: files[@]: #/: syntax error: operand expected (error token is "#/")
Found 951 files to rename
Renaming files...
random_rename_script.sh: line 69: ${#${#actual_files[@]}}: bad substitution
mv: rename temp_rename_89404/* to ./*: No such file or directory
Renaming complete! Files are now in random order when sorted by name.
```
Edit
I see multiple issues with the zsh syntax. Let me fix them:
```
