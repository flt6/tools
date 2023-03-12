# Generater of English listening exam mp3

## Usage

Save the text in `input.txt` and the output file will saved as `02d%.mp3`. If the input file is too lang, the output will be splitted. Please merge them manually.

## Input Format

The conversations should be combined with the readers in the following format:

```plain text
<Symbol>: <Conversation>
```

Note that the there must be a space after `:`.
|Reader|Symbol|Voice name|
|-|-|-|
|Man|M|en-US-EricNeural|
|Woman|W|en-US-JennyMultilingualNeural|
|The Chinese prompt|B|zh-CN-YunfengNeural|

There is also a special symbol for the delay:

```plain text
{delay <Time>}
```

Note that the time is in seconds, and float is accepted.

## Example

This is the common begin for nearly all the exam for senior high.

```plain text
B: 听力考试现在开始
{delay 1}
B: 第一节。听下面三段对话，每段对话后有一道小题，从题中所给的A、B、C三个选项中选出最佳选项。听完每段对话后，你都有十秒钟的时间来回答这一小题和阅读下一小题。每段对话仅读一遍。例如
{delay 1}
B: 现在，你将有5秒钟的时间来阅读试卷上的例题。
{delay 5}
B: 你将听到以下内容
M: Excuse me. Can you tell me how much the shirt is?
W: Yes. It's nine fifteen.
{delay 0.5}
B: 你将有5秒钟时间来把正确答案标在试卷上，衬衫的价格为九磅十五便士，所以你选择C项，并将其标在试卷上。
{delay 0.5}
B: 现在，你有五秒钟的时间来阅读第一小题的有关内容。
{delay 5}
```
