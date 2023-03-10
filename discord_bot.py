import discord
from discord import Colour
import youtube_dl
import random
from discord.ext import commands
import DiscordUtils
import asyncio
from discord.utils import get

token = "NzQxODU1NTQxMTQzMjczNTky.Xy9o0A.TSo-BGMvLgEML04w69lofPRElLs"
client = discord.Client()
queues = []
music = DiscordUtils.Music()
bot = commands.Bot(command_prefix='$')


colours = [Colour.blue(), Colour.blurple(), Colour.dark_blue(), Colour.dark_gold(), Colour.dark_orange(
), Colour.dark_red(), Colour.green(), Colour.magenta(), Colour.orange(), Colour.purple(), Colour.red(), Colour.teal()]


# ytdl_format_options = {
#     'format': 'bestaudio/best',
#     'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
#     'restrictfilenames': True,
#     'noplaylist': True,
#     'nocheckcertificate': True,
#     'ignoreerrors': False,
#     'logtostderr': False,
#     'quiet': True,
#     'no_warnings': True,
#     'default_search': 'auto',
#     # bind to ipv4 since ipv6 addresses cause issues sometimes
#     'source_address': '0.0.0.0'
# }

# ffmpeg_options = {
#     'options': '-vn'
# }

# ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


# class YTDLSource(discord.PCMVolumeTransformer):
#     def __init__(self, source, *, data, volume=0.5):
#         super().__init__(source, volume)

#         self.data = data

#         self.title = data.get('title')
#         self.url = data.get('url')

#     @classmethod
#     async def from_url(cls, url, *, loop=None, stream=False):
#         loop = loop or asyncio.get_event_loop()
#         data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

#         if 'entries' in data:
#             # take first item from a playlist
#             data = data['entries'][0]

#         filename = data['url'] if stream else ytdl.prepare_filename(data)
#         return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@bot.event
async def on_ready():  # checks when bot is ready
    print("Bot is ready")

@bot.command()
async def help_music(ctx):
    async with ctx.typing():
        n = random.randint(0, len(colours)-1)
        embed = discord.Embed(title="Music Commands",
                              description=None, colour=colours[n])
        embed.add_field(
            name="`$join`", value="Use this command to makes bot join the discord channel")
        embed.add_field(name="`$play`", value="Play songs")
        embed.add_field(name="`$queue`", value="Displays Queue")
        embed.add_field(name="`$leave`", value="Leave Voice Chat")
        embed.add_field(name="`$stop`", value="stops currently playing music")
        embed.add_field(name="`$resume`", value="Resumes the Queue")
        embed.add_field(name="`$pause`", value="Pauses the music")
        embed.add_field(name="`$volume`", value="Set Volume")
        embed.add_field(name="`$next`", value="Pays Queue")
    await ctx.send(embed=embed)


@bot.command()
async def clear(ctx, *, n: int):
    try:
        if n < 10001:
            count = n//100
            rem = n % 100
            for i in range(count):
                messages = []
                async for message in ctx.channel.history(limit=100):
                    messages.append(message)
                await ctx.channel.delete_messages(messages)
                await asyncio.sleep(1.2)
            messages = []
            async for message in ctx.channel.history(limit=(rem+1)):
                messages.append(message)
            await ctx.channel.delete_messages(messages)
            k = str(ctx.message.author)+' deleted '+str(n)+' messages.'
            async with ctx.typing():
                num = random.randint(0, len(colours)-1)
                embed = discord.Embed(
                    title="Clear", description=k, colour=colours[num])
            m = await ctx.send(embed=embed)
            await asyncio.sleep(3)
            await ctx.channel.delete_messages([m])
        else:
            async with ctx.typing():
                n = random.randint(0, len(colours)-1)
                embed = discord.Embed(
                    title="Error", description='Cannot clear more than 10,000 msgs at once.', colour=colours[n])
            await ctx.send(embed=embed)
    except:
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Error", description='Permission Error.', colour=colours[n])
        await ctx.send(embed=embed)


@bot.command(pass_context=True)
async def join(ctx):
    if not ctx.message.author.voice:
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Error", description="You are not connected to a voice channel", colour=colours[n])
        await ctx.send(embed=embed)
        return
    else:
        channel = ctx.message.author.voice.channel
    await ctx.author.voice.channel.connect()


@bot.command(pass_context=True, aliases=['rem'])
async def remove(ctx, *, number: str):
    global queues
    if number == "all":
        queues = []
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            o = ""
            for i in range(len(queues)):
                o = o+str(i+1)+") "+queues[i]+'\n'
            embed = discord.Embed(
                title="Queue", description="Your Queue is now empty", colour=colours[n])
        await ctx.send(embed=embed)
    else:
        try:
            number = int(number)
            number = number-1
            del (queues[int(number)])
            async with ctx.typing():
                n = random.randint(0, len(colours)-1)
                o = ""
                for i in range(len(queues)):
                    o = o+str(i+1)+") "+queues[i]+'\n'
                embed = discord.Embed(
                    title="Queue", description="Your Queue is now: \n"+o, colour=colours[n])
            await ctx.send(embed=embed)
        except:
            async with ctx.typing():
                n = random.randint(0, len(colours)-1)
                embed = discord.Embed(
                    title="Error", description='Your queue is either **empty** or the index is **out of range**', colour=colours[n])
            await ctx.send(embed=embed)


@bot.command(aliases=['que'])
async def queue(ctx):
    async with ctx.typing():
        n = random.randint(0, len(colours)-1)
        global queues
        o = ""
        for i in range(len(queues)):
            o = o+str(i+1)+") "+queues[i]+'\n'
        embed = discord.Embed(
            title="Queue", description="Music Queue: \n"+o, colour=colours[n])
    await ctx.send(embed=embed)


@bot.command(pass_context=True)
async def play(ctx, *, url: str):
    print("Play invoked")
    try:
        try:
            if not ctx.message.author.voice:
                async with ctx.typing():
                    n = random.randint(0, len(colours)-1)
                    embed = discord.Embed(
                        title="Error", description="You are not connected to a voice channel", colour=colours[n])
                await ctx.send(embed=embed)
                return
            else:
                channel = ctx.message.author.voice.channel
            await ctx.author.voice.channel.connect()
        except:
            pass
        if not ctx.message.author.voice:
            async with ctx.typing():
                n = random.randint(0, len(colours)-1)
                embed = discord.Embed(
                    title="Error", description="You are not connected to a voice channel", colour=colours[n])
            await ctx.send(embed=embed)
            return
        global queues
        author = ctx.message.author.id
        voice = get(bot.voice_clients, guild=ctx.guild)
        url1 = url+" | <@"+str(author)+">"
        if (voice and voice.is_playing()) or (voice and voice.is_paused()) or len(queues) != 0:
            queues.append(url1)
            async with ctx.typing():
                n = random.randint(0, len(colours)-1)
                embed = discord.Embed(
                    title="Queue Updated", description=f'`{url}` added to queue!', colour=colours[n])
            await ctx.send(embed=embed)
        else:
            player = music.get_player(guild_id=ctx.guild.id)
            if not player:
                player = music.create_player(ctx, ffmpeg_error_betterfix=True)
            if not ctx.voice_client.is_playing():
                await player.queue(url, bettersearch=True)
                song = await player.play()
                async with ctx.typing():
                    n = random.randint(0, len(colours)-1)
                    embed = discord.Embed(
                        title="Now Playing", description=f"Playing {song.name}"+" | <@"+str(author)+">", colour=colours[n])
                await ctx.send(embed=embed)
    except:
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(title="Error", description="<@"+str(author)+">" +
                                  "Some error occurred. Try $restart to restart the bot.", colour=colours[n])
        await ctx.send(embed=embed)


@bot.command(aliases=['nxt'])
async def next(ctx):
    try:
        player = music.get_player(guild_id=ctx.guild.id)
        voice = get(bot.voice_clients, guild=ctx.guild)
        if (voice and voice.is_paused()) or (voice and voice.is_playing()):
            voice.stop()
        try:
            async with ctx.typing():
                global queues
                server = ctx.message.guild
                voice_channel = server.voice_client
                i = queues[0]
                i = i.split("|")
                await player.queue(i[0], bettersearch=True)
                song = await player.play()
                n = random.randint(0, len(colours)-1)
                embed = discord.Embed(
                    title="NOW Playing", description=f"Playing "+str(song.name)+" "+i[1], colour=colours[n])
                await ctx.send(embed=embed)
            del (queues[0])
        except AttributeError:
            async with ctx.typing():
                n = random.randint(0, len(colours)-1)
                embed = discord.Embed(
                    title="Error", description="Please Connect to a voice channel", colour=colours[n])
            await ctx.send(embed=embed)
    except:
        i = queues[0]
        i = i.split("|")
        del (queues[0])
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Error", description=i[1]+" The url is not supported currently. Try to search for a different video.", colour=colours[n])
        await ctx.send(embed=embed)


@bot.command(aliases=['pau'])
async def pause(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_playing():
        voice.pause()
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Voice", description="Music Paused!", colour=colours[n])
        await ctx.send(embed=embed)
    else:
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Voice", description="No music Playing or some error occured.", colour=colours[n])
        await ctx.send(embed=embed)


@bot.command(aliases=['res'])
async def resume(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_paused():
        voice.resume()
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Voice", description="Music Resumed!", colour=colours[n])
        await ctx.send(embed=embed)
    else:
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Voice", description="No music Paused or some error occured.", colour=colours[n])
        await ctx.send(embed=embed)


@bot.command(aliases=['lev'])
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()


@bot.command()
async def stop(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if (voice and voice.is_paused()) or (voice and voice.is_playing()):
        voice.stop()
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Voice", description="Current Music Stopped and Removed from queue!", colour=colours[n])
        await ctx.send(embed=embed)
    else:
        async with ctx.typing():
            n = random.randint(0, len(colours)-1)
            embed = discord.Embed(
                title="Voice", description="No music Paused or Playing or some error occured.", colour=colours[n])
        await ctx.send(embed=embed)


@bot.command(aliases=['vol'])
async def volume(ctx, vol: float):
    async with ctx.typing():
        author = ctx.message.author.id
        player = music.get_player(guild_id=ctx.guild.id)
        # volume should be a float between 0 to 1
        song, volume = await player.change_volume(float(vol / 100))
        n = random.randint(0, len(colours)-1)
        embed = discord.Embed(
            title="Volume", description=f"Changed volume for {song.name} to {volume*100}%"+" | <@"+str(author)+">", colour=colours[n])
    await ctx.send(embed=embed)

bot.run(token)
