LoadEverything().then(() => {
  
  gsap.config({ nullTargetWarn: false, trialWarn: false });

  let startingAnimation = gsap
    .timeline({ paused: true })
    .from([".logo"], { duration: 0.5, autoAlpha: 0, ease: "power2.inOut" }, 0.5)
    .from(
      [".anim_container_outer"],
      {
        duration: 1,
        width: "0",
        ease: "power2.inOut",
      },
      1
    )
    .from(
      [".info.bottom"],
      {
        duration: 1,
        autoAlpha: 0,
        ease: "power2.inOut",
      },
      1
    )
    .from(
      [".fgc .top", ".fgc .player"],
      {
        duration: 1,
        y: "-100px",
        ease: "power2.inOut",
      },
      0
    )
    .from(
      [".fgc:not(.bblue) .bottom"],
      {
        duration: 1,
        y: "+100px",
        ease: "power2.inOut",
      },
      0
    )
    .from(
      [".fgc.bblue .bottom"],
      {
        duration: 1,
        autoAlpha: 0,
        ease: "power2.inOut",
      },
      0.2
    );

  Start = async () => {
    startingAnimation.restart();
  };

  Update = async (event) => {
    let data = event.data;
    let oldData = event.oldData;

    let isTeams = Object.keys(data.score[window.scoreboardNumber].team["1"].player).length > 1;

    if (!isTeams) {
      for (const [t, team] of [
        data.score[window.scoreboardNumber].team["1"],
        data.score[window.scoreboardNumber].team["2"],
      ].entries()) {
        for (const [p, player] of [team.player["1"]].entries()) {
          if (player) {
            SetInnerHtml(
              $(`.p${t + 1}.container .name`),
              `
                <span class="sponsor">
                  ${player.team ? player.team : ""}
                </span>
                ${await Transcript(player.name)}
                ${team.losers ? "<span class='losers'>L</span>" : ""}
              `
            );

            SetInnerHtml(
              $(`.p${t + 1} .flagcountry`),
              player.country.asset
                ? `
                  <div class='flag' style='background-image: url(../../${player.country.asset.toLowerCase()})'></div>
                  <div>${player.country.code}</div>
                `
                : ""
            );

            SetInnerHtml(
              $(`.p${t + 1} .flagstate`),
              player.state.asset
                ? `
                  <div class='flag' style='background-image: url(../../${player.state.asset})'></div>
                  <div>${player.state.code}</div>
                `
                : ""
            );

            await CharacterDisplay(
              $(`.p${t + 1}.container .character_container`),
              {
                asset_key: "base_files/icon",
                source: `score.${window.scoreboardNumber}.team.${t + 1}`,
              },
              event
            );

            SetInnerHtml(
              $(`.p${t + 1}.container .sponsor_icon`),
              player.sponsor_logo
                ? `<div style='background-image: url(../../${player.sponsor_logo})'></div>`
                : ""
            );

            SetInnerHtml(
              $(`.p${t + 1}.container .avatar`),
              player.avatar
                ? `<div style="background-image: url('../../${player.avatar}')"></div>`
                : ""
            );

            SetInnerHtml(
              $(`.p${t + 1}.container .online_avatar`),
              player.online_avatar
                ? `<div style="background-image: url('${player.online_avatar}')"></div>`
                : ""
            );

            SetInnerHtml(
              $(`.p${t + 1} .twitter`),
              player.twitter
                ? `<span class="twitter_logo"></span>${String(player.twitter)}`
                : ""
            );

            SetInnerHtml(
              $(`.p${t + 1} .pronoun`),
              player.pronoun ? player.pronoun : ""
            );

            SetInnerHtml(
              $(`.p${t + 1} .seed`),
              player.seed ? `Seed ${player.seed}` : ""
            );

            SetInnerHtml($(`.p${t + 1}.container .score`), String(team.score));

            SetInnerHtml(
              $(`.p${t + 1}.container .sponsor-container`),
              `<div class='sponsor-logo' style='background-image: url(../../${player.sponsor_logo})'></div>`
            );

            if ($(".sf6.online").length > 0) {
              console.log(player.twitter);
              console.log(player.pronoun);
              if (!player.twitter && !player.pronoun) {
                gsap.to($(`.p${t + 1}.chips`), { autoAlpha: 0 });
              } else {
                gsap.to($(`.p${t + 1}.chips`), { autoAlpha: 1 });
              }
            }
          }
        }
        if(team.color) {
          document.querySelector(':root').style.setProperty(`--p${t + 1}-score-bg-color`, team.color);
        }
      }
    } else {
      for (const [t, team] of [
        data.score[window.scoreboardNumber].team["1"],
        data.score[window.scoreboardNumber].team["2"],
      ].entries()) {
        let teamName = team.teamName;

        let names = [];
        for (const [p, player] of Object.values(team.player).entries()) {
          if (player && player.name) {
            names.push(await Transcript(player.name));
          }
        }
        let playerNames = names.join(" / ");

        if (!team.teamName || team.teamName == "") {
          teamName = playerNames;
        }

        SetInnerHtml(
          $(`.p${t + 1}.container .name`),
          `
            ${teamName}
            ${team.losers ? "<span class='losers'>L</span>" : ""}
          `
        );

        SetInnerHtml($(`.p${t + 1} .flagcountry`), "");

        SetInnerHtml($(`.p${t + 1} .flagstate`), "");

        await CharacterDisplay(
          $(`.p${t + 1}.container .character_container`),
          {
            asset_key: "base_files/icon",
            source: `score.${window.scoreboardNumber}.team.${t + 1}`,
            slice_character: [0, 1],
          },
          event
        );

        SetInnerHtml($(`.p${t + 1}.container .sponsor_icon`), "");

        SetInnerHtml($(`.p${t + 1}.container .avatar`), "");

        SetInnerHtml($(`.p${t + 1}.container .online_avatar`), "");

        SetInnerHtml($(`.p${t + 1} .twitter`), 
          playerNames != team.teamName ? playerNames : ""
        );

        SetInnerHtml($(`.p${t + 1}.container .score`), String(team.score));

        SetInnerHtml($(`.p${t + 1}.container .sponsor-container`), "");

        if(team.color) {
          document.querySelector(':root').style.setProperty(`--p${t + 1}-score-bg-color`, team.color);
        }
      }
    }

    SetInnerHtml($(".tournament_name"), data.tournamentInfo.tournamentName);

    SetInnerHtml($(".match"), data.score[window.scoreboardNumber].match);

    let phaseTexts = [];
    if (data.score[window.scoreboardNumber].phase) phaseTexts.push(data.score[window.scoreboardNumber].phase);
    if (data.score[window.scoreboardNumber].best_of_text) phaseTexts.push(data.score[window.scoreboardNumber].best_of_text);

    SetInnerHtml($(".phase"), phaseTexts.join(" - "));
  };
});
