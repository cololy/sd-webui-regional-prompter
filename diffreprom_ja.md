# DiffReprom
DiffRepromは、hako-mikan氏作成のDifferential Regional Prompterのfork版スクリプトです。t2iでプロンプトのみで、指定した領域だけを変更した差分画像を生成できます。次の画像はこのスクリプトを用いて生成した差分です。2枚目が表情を変更、3枚目が表情と髪飾りと服装を変更したものです。  
<img src="https://github.com/cololy/sd-webui-regional-prompter/blob/imgs/diffsample1.jpg" width="400">  
<img src="https://github.com/cololy/sd-webui-regional-prompter/blob/imgs/diffsample2.jpg" width="400">  
<img src="https://github.com/cololy/sd-webui-regional-prompter/blob/imgs/diffsample3.jpg" width="400">

人物全体を変更した3枚目においても、人物から離れた部分の背景は元画像と同じになり、ある程度差分画像の一貫性を保ちやすくなっています。マスク作業や元画像の用意が不要で、プロンプトのみで差分画像を生成できるため、差分付き画像を多数生成するのに向いているかと思います。

基本的な仕組みはfork元と同じなので、まずは[Differential Regional Prompter](https://github.com/cololy/sd-webui-regional-prompter/blob/main/differential_ja.md)の説明をお読みください。DiffRepromにおいては上記の例のように、差分を取る領域を複数指定できるようになっています。fork元と同じく、A1111のみで動作します。Forgeは非対応です。

## 画面説明
Differential Regional Prompterから追加された項目のみ説明します。

<img src="https://github.com/cololy/sd-webui-regional-prompter/blob/imgs/diffui.jpg" width="800">

### Threshold Decrease
1stepごとにThresholdを下げる下げ幅を指定できます。大きい領域は徐々にThresholdを下げると良い結果になりやすいです。

### Batch Count
A1111のBatch Countの代わりになる機能です。
A1111本体側のBatch Count、Batch Sizeは1にしてください。

### Seeds
「`,`」区切りでシード値を直接指定します。

### Plus seeds
「`,`」区切りの値に、A1111本体側のシード値を足したシード値を用います。  
例：A1111のシードが20、Plus seedsが0,3,4のとき、シード20,23,24で生成します。

## 使用例

### 表情の変化
冒頭で例示した笑顔、閉じた目、開いた口の表情の作成例を解説します。
まずはベースプロンプトとして、通常のプロンプト欄に以下を入力します。
```
1girl, blue eyes, eyebrows, face, hairclip, shirt and skirt, garden
```
この例では表情を変えるために、`eyes`と`eyebrows`と`face`の3つの領域を使用します。この3つのプロンプトが全てベースプロンプトに入っている必要があります。ただし、SDXLではベースプロンプトに`eyes`だけ入っていても、良い具合の領域が作れないことがあります。`blue eyes`のように目の色を入れると上手く領域を作れます。

次にRegional Prompterのthresholdの設定欄に値を入力します。3領域あるので3つ値が必要です。
thresholdの適正値は、特にSDXLではモデルによって大幅に異なります。
この例ではebara_pony_1のモデルを使用し、thresholdに`0.02,0.02,0.2`を入力しています。  
なお、その他設定値はStep:30 CFG scale:7 Size:768x1152 Sampler:Euler a としています。

次にScheduleに以下を入力します。

```
0
%;smile,(closed eyes:1.7);eyes;1;10;0
-;smile;eyebrows;1;12;0
-;smile,(open mouth:1.2);face;1;12;0
```

その後Generateを押すと、表情の違う2枚の差分画像が生成されます。  
それでは、以下でScheduleの書式を解説します。

```
%;prompt;prompt for region;weight;step;threshold decrease
-;prompt;prompt for region;weight;step;threshold decrease
```
のように`;`で区切って設定値を入力します。

#### `%`
1領域目であることを示すマーク
#### `-`
2領域目以降であることを示すマーク
#### prompt
差分作成用のプロンプト
#### prompt for region
領域計算用のプロンプト
#### weight
プロンプトの強さ
#### step(省略可)
差分作成用のプロンプトが有効になるステップ数  
内部的にこのステップまではthresholdが高くなり、領域の面積は0になる
#### threshold decrease(省略可)
1ステップごとのthresholdの下げ幅

smile,(open mouth:1.2);face;1;12;0の所では、総step数30として、[:(smile,(open mouth:1.2):1):0.4]のプロンプトが生成されます。

なお書式について、1領域目の`%`は省略可能です。2領域目以降の`-`の数は1個以上であれば、複数あっても良いです。2領域目以降で改行しなくても構いません。そのため以下のような記述でも同じ意味になります。
```
0
smile,(closed eyes:1.7);eyes;1;10;0;---;smile;eyebrows;1;12;0;---;smile,(open mouth:1.2);face;1;12;0
```

### 服の変化
次の例ではhairclipをhair flowerに変えて、shirtとskirtをfloral print kimonoとhakamaに変えてみます。ベースプロンプトはそのまま使います。先ほどの表情だけ変化させたScheduleは残して、3枚目の差分として追加してみます。

```
0
th=0.02,0.02,0.2,0.2,0.02
%;smile,(closed eyes:1.7);eyes;1;10;0
-;smile;eyebrows;1;12;0
-;smile,(open mouth:1.2);face;1;12;0
%;smile,(closed eyes:1.7);eyes;1;10;0
-;smile;eyebrows;1;12;0
-;smile,(open mouth:1.2);face;1;12;0
-;(hair flower:1.4),(hairclip:-1.0);(hairclip:0);1;6;0
-;(floral print kimono, hakama:1.4);(shirt and skirt:0);1;6;0.0005
```

領域が5つに増えるので、thresholdの設定数も増やす必要があります。Regional Prompterのthresholdの設定欄に書く代わりに、この例のようにth=～の書式でもthresholdを変えることができます。

hair flowerを強調してもhairclipが残りがちなので、拡張機能の[NegPiP](https://github.com/hako-mikan/sd-webui-negpip/)を用いて、(hairclip:-1.0)でhairclipを消しています。領域計算用のプロンプトもhairclipではなく(hairclip:0)としています。

面積が大きい服の領域では、threshold decreaseを0.0005として、徐々にThresholdを下げています。

### 特殊機能

#### weight、step連続変更機能について
Differential Regional Prompterで説明されているweight、step連続変更機能は、1領域目でのみ使用できます。

#### ベースプロンプトに領域計算用プロンプトを追加

```
0
%;smile,(closed eyes:1.7);eyes;1;10;0
--;smile;eyebrows;1;12;0
--%ap;smile,(open mouth:1.2);face;1;12;0
```

領域の冒頭部に%apを追加すると、ベースプロンプトに後から領域計算用プロンプトを追加します。この例ではベースプロンプトにfaceが入ってなくても、faceを領域計算用プロンプトとして使えるようになります。必要なthreshold値が安定し辛いですが、ベースプロンプトを変えたくない場合に使用できます。

#### ベースプロンプトの置き換え

```
0
%;smile,(closed eyes:1.7);eyes;1;10;0
--;smile;eyebrows;1;12;0
--;smile,(open mouth:1.2);face;1;12;0
--;(hair flower:1.4),(hairclip:-1.0);(hairclip:0);1;6;0
--;(floral print kimono, hakama:1.4);(shirt and skirt:0);1;6;0.0005
--%p;hairclip;[hairclip:(hairclip:0):1.0]
```

冒頭部に%pを追加すると、ベースプロンプトを置換する指令が使えます。この指令は通常と違い、領域計算は行わず、純粋に置換をするだけです。`-%p;置換対象語;置換後の語`のように書きます。  
NegPiPでも元のプロンプトの影響が消しきれない場合等に、元のプロンプトの影響を弱める用途に使用します。最初のステップから変えてしまうと差分の出来が悪くなるため、この例のようにPrompt Edittingの書式を使って、後のステップからプロンプトを変更するとよいです。

<br>
DiffRepromの基本的な使い方の説明は以上になります。 
 
***

## Tips
Dynamic PromptsやADetailerとの併用など、より実践的な使用のためのTipsです。

### Dynamic Promptsとの併用
この機能は内部的にベースプロンプトを複製しています。Dynamic Promptsを直接使用すると、複製したプロンプトごとに選ばれるプロンプトが変わるため、差分の出来が悪くなります。  
${color=!\_\_eyecolor\_\_}のように!付きの変数に一旦格納して固定してから、${color}で変数を呼び出す形で使用してください。

```
1girl, ${color} eyes, eyebrows, face, hairclip, shirt and skirt, ${location}
${color=!__eyecolor__}${location=!{garden|fountain}}
```

Scheduleでも変数を使用すると便利です。  
適宜{|}等を挟むと前差分と乱数を変えられます。

```
0
%;${e=!{smile|angry|sad}}${mouth=!{(open mouth:1.2)|(open mouth:0.6)|(closed mouth:1.2)}}${eye=!{|(closed eyes:1.7)}}${e},${eye};eyes;1;10;0
--;${e};eyebrows;1;12;0
--;${e},${mouth};face;1;12;0
%;${e=!{|}{smile|angry|sad}}${mouth=!{(open mouth:1.2)|(open mouth:0.6)|(closed mouth:1.2)}}${eye=!{|(closed eyes:1.7)}}${e},${eye};eyes;1;10;0
--;${e};eyebrows;1;12;0
--;${e},${mouth};face;1;12;0
```

### Wildcards内のLora
DiffRepromではベースプロンプト複製の際、Loraは除外していますが、Wildcards内のLoraは複製されてしまいます。Loraのweightを下げて使用してください。  
Scheduleの冒頭にr=9のように書くと、対象領域が9個に満たない時でも9回までベースプロンプトを複製します。

```
r=9
0
%;smile,(closed eyes:1.7);eyes;1;10;0
--;smile;eyebrows;1;12;0
--%ap;smile,(open mouth:1.2);face;1;12;0
```

r=9なら1/(1+9)=1/10倍にLoraのweightを下げます。

### ADetailerとの併用
この機能の内部でベースプロンプトが多数複製されるため、ADetailerにそのままプロンプトを送ると表情プロンプトが埋もれやすくなります。またADetailerではPrompt Edittingのstepが0からやり直しになるため、表情が反映され辛いです。

表情を反映させやすくするためには、fork版の[ADetailer](https://github.com/cololy/adetailer)を使用すると良いです。

fork版ではADetailerに送るPromptを以下の用に変更する機能があります。
- Prompt Edittingの整数Step表記、または2.0未満の小数Step表記を0にし、2.xの小数Step表記は0.xに変更する。
- \<noad1:1>以降のプロンプトを削除する。  
  2ndモデルで機能させる場合は\<noad2:1>、1stでも2ndでも機能させる場合は\<noad:1>のように記載。
- \<noad1a:1>から\<noad1b:1>までのプロンプトを削除する。
- \<pad1:～>を～に変更する。
- \<lad1:～>を\<lora:～>に変更する

```
1girl, blue eyes <noad1a:1> ,shirt, skirt <noad1b:1> [:,smile:1.0] <pad1:,open mouth> <lad1:facetest:1>  <noad1:1> ,garden, flower
```
このプロンプトはADetailerの1stモデルでは以下のように変更されます。

```
1girl, blue eyes  [:,smile:0] ,open mouth <lora:facetest:1>
```

### 領域計算用のプロンプトについて
- 領域計算用のプロンプトはなるべく冒頭に近い位置に置く方が、必要thresholdが安定しやすいです。
- thresholdを下げていくと、領域計算用のプロンプトのすぐ後ろに置かれたプロンプトの領域が巻き込まれやすい傾向にあります。間に他のプロンプトを挟むと巻き込みが防ぎやすくなります。

### NegPiPとの併用
NegPiP使用の際、Prompt Edittingのステップ数を整数で書くと画像がおかしくなることがあります。
stepの設定値は小数に変換されますが、直接Prompt Edittingの書式を書く場合はご注意ください。

### Prompt Edittingのトークン数
Prompt Editting使用時に75トークンの閾値をまたぐと画像がおかしくなることがあります。トークン数を揃えておくのが無難です。もしくは適宜BREAKを入れると良いです。
